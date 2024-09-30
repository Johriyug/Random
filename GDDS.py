import pyaudio
import numpy as np
import time
from pynput import keyboard  
from gtts import gTTS
import os
import sounddevice as sd

def speak(text):
    tts = gTTS(text=text, lang='en')
    tts.save("temp.mp3")
    os.system("afplay temp.mp3")

# Parameters
CHUNK = 1024         
FORMAT = pyaudio.paInt16  
CHANNELS = 1        
RATE = 44100        
THRESHOLD = 20000  # Adjust based on microphone sensitivity
REFERENCE_INTENSITY = 1e-12  # Threshold of hearing (W/m²)
SOUND_SPEED = 343  # Speed of sound in air (m/s)
CALIBRATION_DISTANCE = 0.2  # Calibration distance in meters
DURATION = 2  # Duration of sound recording
SAMPLE_RATE = 22050  # Sample rate for sound recording
SOUND_ATTENUATION = 4  # dB attenuation per meter, more realistic for close distances
REFERENCE_DECIBEL_LEVEL = 80  # SPL measured at 0.2 meters 
MIC_SENSITIVITY_CORRECTION = 1.5  # Adjust based on microphone sensitivity

# Initialize PyAudio
p = pyaudio.PyAudio()
stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)

def calculate_rms(audio_data):
    """Calculate the Root Mean Square (RMS) of the audio data."""
    return (np.mean(np.square(audio_data)))**0.5

def calculate_sound_power(rms_value):
    """Calculate the sound power from the RMS value."""
    return rms_value**2

def record_audio(duration, sample_rate):
    """Record audio for a given duration and sample rate."""
    print("Recording...")
    audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='float64')
    sd.wait()  # Wait until recording is finished
    print("Recording finished.")
    return audio_data.flatten()

def calibrate_intensity_db(reference_distance, intensity_db):
    """Calibrate the system using a known reference sound level at a known distance."""
    return intensity_db - 20 * np.log10(reference_distance / CALIBRATION_DISTANCE)

def calculate_intensity_db(intensity):
    """Calculate decibel level from intensity."""
    intensity_db = 10 * np.log10(intensity / REFERENCE_INTENSITY)
    return intensity_db

def calculate_distance(intensity_db):
    """Estimate distance based on intensity drop-off."""
    # Using inverse square law for sound, calibrate the sound attenuation for short distances
    distance = CALIBRATION_DISTANCE * 10 ** ((REFERENCE_DECIBEL_LEVEL - intensity_db) / (20 * SOUND_ATTENUATION))
    return distance * MIC_SENSITIVITY_CORRECTION  # Adjust for microphone sensitivity

stop_detection = False

def on_press(key):
    global stop_detection
    try:
        if key.char == 'q':
            print("Quitting...")
            stop_detection = True
    except AttributeError:
        pass

# if key is pressed
listener = keyboard.Listener(on_press=on_press)
listener.start()

print("Press 'q' to quit...")

def main():
    # Record audio
    audio_data = record_audio(DURATION, SAMPLE_RATE)
    
    # Calculate RMS of the audio signal
    rms_value = calculate_rms(audio_data)
    
    # Calculate sound power
    sound_power = calculate_sound_power(rms_value)
    return sound_power

try:
    while not stop_detection:
        try:
            # Read audio data from the stream
            data = np.frombuffer(stream.read(CHUNK, exception_on_overflow=False), dtype=np.int16)
            # Calculating intensity
            intensity = np.max(np.abs(data))
            sound_detected = intensity > THRESHOLD
            
            if sound_detected:
                # Calculate sound power and convert it to decibels
                sound_power = main()
                intensity_db = calculate_intensity_db(sound_power)
                
                # Calibrate decibel level based on known reference
                calibrated_db = calibrate_intensity_db(CALIBRATION_DISTANCE, intensity_db)
                
                # Calculate distance based on calibrated intensity in decibels
                distance = calculate_distance(calibrated_db)

                print(f"Alert, Gunshot detected!!!")
                print(f"Calibrated Intensity: {round(calibrated_db, 2)} dB")
                #print(f"Distance: {round(distance, 2)} meters")
                
                # Trigger audio alert
                speak(f"Alert, Gunshot detected!!! with intensity {round(calibrated_db, 2)} decibels.")
                
                time.sleep(1)  # Brief delay to avoid multiple detections
                
        except OSError as e:
            print(f"Error reading from the stream: {e}")
            continue

except KeyboardInterrupt:
    print("Interrupted by user.")

finally:
    # Cleanup resources with additional error handling
    try:
        if stream.is_active():
            stream.stop_stream()
        stream.close()
    except Exception as e:
        print(f"Error stopping or closing the stream: {e}")
    finally:
        p.terminate()
        listener.stop()