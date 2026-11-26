import json
import zipfile
from pathlib import Path
import numpy as np
import requests
import sounddevice as sd
from vosk import KaldiRecognizer, Model, SetLogLevel

HZ = 16000
COLORES = ["\033[96m", "\033[93m", "\033[95m", "\033[92m", "\033[91m", "\033[94m"]
CACHE = Path.home() / ".cache" / "vosk"
WEB = requests.Session()

def pedir(pregunta):
    texto = input(pregunta).strip().lower()
    return "ca" if texto in ("ca", "cat", "catalan", "català") else texto
def modelo(idioma):
    codigo = "en-us" if idioma == "en" else idioma
    for sitio in (Path(__file__).parent, CACHE):
        if not sitio.is_dir():
            continue
        for carpeta in sitio.iterdir():
            if carpeta.is_dir() and f"-{codigo}" in carpeta.name and (carpeta / "am").is_dir():
                return Model(str(carpeta))
    CACHE.mkdir(parents=True, exist_ok=True)
    lista = WEB.get("https://alphacephei.com/vosk/models/model-list.json", timeout=20).json()
    nombre = next(m["name"] for m in lista if m["lang"] == codigo and m["type"] == "small" and m["obsolete"] == "false")
    archivo = CACHE / f"{nombre}.zip"
    try:
        zipfile.ZipFile(archivo).close()
    except (FileNotFoundError, zipfile.BadZipFile):
        print("Descargando el modelo. La próxima vez ya estará guardado.")
        r = WEB.get(f"https://alphacephei.com/vosk/models/{nombre}.zip", timeout=180)
        r.raise_for_status()
        archivo.write_bytes(r.content)
    zipfile.ZipFile(archivo).extractall(CACHE)
    return Model(str(CACHE / nombre))
def traducir(texto, origen, destino):
    if origen == destino:
        return texto
    r = WEB.get("https://clients5.google.com/translate_a/t", params={"client": "dict-chrome-ex", "sl": origen, "tl": destino, "dt": "t", "q": texto}, timeout=4)
    r.raise_for_status()
    trozo = r.json()[0]
    return trozo if isinstance(trozo, str) else "".join(p[0] for p in trozo if p and p[0])
def tono(muestras):
    if len(muestras) < 3200:
        return None
    senal = muestras[-8000:].astype("float32")
    senal -= senal.mean()
    if np.max(np.abs(senal)) < 400:
        return None
    parecido = np.correlate(senal, senal, mode="full")[len(senal) - 1 :]
    desde, hasta = HZ // 400, HZ // 70
    zona = parecido[desde:hasta]
    periodo = desde + int(np.argmax(zona))
    return None if parecido[periodo] < 0.3 * parecido[0] else HZ / periodo
def hablante(frecuencia, voces):
    if frecuencia is None:
        return 0
    for i, voz in enumerate(voces):
        # Menos de 4 semitonos: es la misma persona.
        if abs(12 * np.log2(frecuencia / voz)) < 4:
            voces[i] = voz * 0.85 + frecuencia * 0.15
            return i
    voces.append(frecuencia)
    return len(voces) - 1
def main():
    origen = pedir("Hablas (en, es, ca, it...): ")
    destino = pedir("Traducir a (en, es, ca, it...): ")
    SetLogLevel(-1)
    print("Cargando... Ctrl+C para parar.")
    reconocedor = KaldiRecognizer(modelo(origen), HZ)
    voces, tonos, ultimo, color = [], [], "", None
    frase = salida = None
    mostrado = True
    audio = np.zeros(0, dtype="int16")
    paso = 0
    with sd.InputStream(samplerate=HZ, channels=1, dtype="int16", blocksize=320, latency="low") as mic:
        while True:
            bloque, _ = mic.read(320)
            bloque = np.asarray(bloque).ravel()
            audio = np.concatenate((audio, bloque))[-HZ:]
            paso += 1
            if paso % 5 == 0:
                frecuencia = tono(audio)
                if frecuencia:
                    tonos.append(frecuencia)
            cerrado = reconocedor.AcceptWaveform(bloque.tobytes())
            datos = json.loads(reconocedor.Result() if cerrado else reconocedor.PartialResult())
            texto = (datos.get("text") or datos.get("partial") or "").strip()
            if texto and texto != ultimo:
                ultimo = texto
                frase = texto[0].upper() + texto[1:]
                try:
                    salida = traducir(frase, origen, destino)
                except Exception as error:
                    print(f"\n{error}")
                    salida = None
                mostrado = False
            if color is None and salida and tonos and (len(tonos) >= 4 or cerrado):
                media = float(np.median(tonos))
                color = COLORES[hablante(media, voces) % len(COLORES)]
            if color and salida and not mostrado:
                linea = frase if salida == frase else f"{salida} ({frase})"
                print(f"\r{color}{linea}\033[0m", end="\n" if cerrado else "", flush=True)
                mostrado = True
            if cerrado:
                color, tonos, audio = None, [], np.zeros(0, dtype="int16")
                frase = salida = None
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
