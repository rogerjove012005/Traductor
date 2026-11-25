import numpy as np

def decibelios(audio):
    rms = np.sqrt(np.mean(audio ** 2))
    return 20 * np.log10(rms)