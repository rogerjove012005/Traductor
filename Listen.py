import threading

import requests
from deep_translator import GoogleTranslator
from deep_translator.exceptions import (
    InvalidSourceOrTargetLanguage,
    LanguageNotSupportedException,
)
import sounddevice as sd
import speech_recognition as sr


def pedir_idioma():
    print("¿En qué idioma quieres la respuesta? (en, es, it...)")
    while True:
        idioma = input("Idioma: ").strip().lower()
        try:
            GoogleTranslator(source="es", target=idioma)
        except (InvalidSourceOrTargetLanguage, LanguageNotSupportedException):
            print("Ese idioma no está disponible. Prueba con en, es, it, fr o de.")
            continue
        return idioma


def traducir_google(texto, idioma):
    response = requests.get(
        "https://clients5.google.com/translate_a/t",
        params={
            "client": "dict-chrome-ex",
            "sl": "es",
            "tl": idioma,
            "dt": "t",
            "q": texto,
        },
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    if data and isinstance(data[0], str):
        return "".join(data)
    return "".join(parte[0] for parte in data[0] if parte and parte[0])


def traducir_mymemory(texto, idioma):
    response = requests.get(
        "https://api.mymemory.translated.net/get",
        params={"q": texto, "langpair": f"es|{idioma}"},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    traducido = (data.get("responseData") or {}).get("translatedText", "")
    if data.get("responseStatus") != 200 or "MYMEMORY WARNING" in traducido.upper():
        raise requests.RequestException(traducido or "MyMemory no pudo traducir")
    return traducido


def traducir(texto, idioma):
    if idioma == "es":
        return texto
    ultimo_error = None
    for servicio in (traducir_google, traducir_mymemory):
        try:
            return servicio(texto, idioma)
        except requests.RequestException as error:
            ultimo_error = error
    raise ultimo_error


def main():
    idioma = pedir_idioma()
    recognizer = sr.Recognizer()
    recognizer.operation_timeout = 10
    parar = threading.Event()

    print("Habla en español. Transcribo por fragmentos; pulsa Enter para parar.")
    threading.Thread(
        target=lambda: (input(), parar.set()), daemon=True
    ).start()

    try:
        while not parar.is_set():
            grabacion = sd.rec(
                44100 * 5,
                samplerate=44100,
                channels=1,
                dtype="int16",
            )
            sd.wait()
            try:
                text = recognizer.recognize_google(
                    sr.AudioData(grabacion.tobytes(), 44100, 2), language="es-ES"
                ).strip()
            except sr.UnknownValueError:
                continue
            except sr.RequestError as error:
                print(f"No se pudo conectar con el servicio de transcripción: {error}")
                break

            if text:
                text = text[0].upper() + text[1:]
                if text[-1] not in ".!?":
                    text = text.rstrip(" ,;:") + "."
                try:
                    respuesta = traducir(text, idioma)
                except Exception as error:
                    print(f"No se pudo traducir el fragmento: {error}")
                    continue
                if respuesta == text:
                    print(respuesta)
                else:
                    print(f"{respuesta} ({text})")
    except KeyboardInterrupt:
        print("\nDeteniendo la escucha...")

if __name__ == "__main__":
    main()

