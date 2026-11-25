import threading

import sounddevice as sd
import speech_recognition as sr

def main():
    recognizer = sr.Recognizer()
    recognizer.operation_timeout = 10
    parar = threading.Event()
    textos = []

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
                textos.append(text)
                print(text)
    except KeyboardInterrupt:
        print("\nDeteniendo la escucha...")
    finally:
        print("\nTexto completo:")
        print(" ".join(textos) if textos else "(No se reconoció voz)")


if __name__ == "__main__":
    main()
