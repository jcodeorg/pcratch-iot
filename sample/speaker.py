from machine import Pin, PWM
import time

speaker = PWM(Pin(21))

notes = {
    "C": 262,
    "D": 294,
    "E": 330,
    "F": 349,
    "G": 392,
    "A": 440,
    "B": 494,
    "C5": 523
}

def play(note, duration=0.4):
    speaker.freq(notes[note])
    speaker.duty_u16(30000)
    time.sleep(duration)
    speaker.duty_u16(0)
    time.sleep(0.05)

melody = ["C", "D", "E", "F", "G", "A", "B", "C5"]

for n in melody:
    play(n)

speaker.deinit()
