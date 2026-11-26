import json
from pathlib import Path

import requests
import sounddevice as sd
from vosk import KaldiRecognizer, Model, SetLogLevel

HZ = 16000
sesion = requests.Session()


def modelo(idioma):
    if idioma == "es":
        return Model(str(Path(__file__).with_name("vosk-model-small-es-0.42")))
    return Model(lang="en-us" if idioma == "en" else idioma)


def traducir(texto, origen, destino):
    if origen == destino:
        return texto
    r = sesion.get(
        "https://clients5.google.com/translate_a/t",
        params={"client": "dict-chrome-ex", "sl": origen, "tl": destino, "dt": "t", "q": texto},
        timeout=4,
    )
    r.raise_for_status()
    dato = r.json()[0]
    return dato if isinstance(dato, str) else "".join(p[0] for p in dato if p and p[0])


def main():
    origen = input("Hablas (en, es, it...): ").strip().lower()
    destino = input("Traducir a (en, es, it...): ").strip().lower()
    SetLogLevel(-1)
    print("Cargando... Ctrl+C para parar.")
    rec = KaldiRecognizer(modelo(origen), HZ)
    ultimo = ""

    with sd.InputStream(samplerate=HZ, channels=1, dtype="int16", blocksize=320, latency="low") as mic:
        while True:
            audio, _ = mic.read(320)
            fin = rec.AcceptWaveform(audio.tobytes())
            datos = json.loads(rec.Result() if fin else rec.PartialResult())
            texto = (datos.get("text") or datos.get("partial") or "").strip()
            if not texto or texto == ultimo:
                continue
            ultimo = texto
            frase = texto[0].upper() + texto[1:]
            try:
                salida = traducir(frase, origen, destino)
            except Exception as error:
                print(f"\n{error}")
                continue
            linea = frase if salida == frase else f"{salida} ({frase})"
            print("\r" + linea, end="\n" if fin else "", flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
