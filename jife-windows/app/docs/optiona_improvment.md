A) Audio cleanup (this matters 
a lot
 for Japanese TV)


Pick ONE of these (in descending impact):

Vocal isolation (best, if you can tolerate a bit more latency/compute)

If you can separate dialogue from music/background, Whisper accuracy jumps. (Demucs/MDX-style vocal separation is the idea.)



Pro: huge boost on TV

Con: adds latency/complexity



Noise suppression + leveling



Normalize loudness (prevents Whisper from “dropping” quiet speakers)

Light denoise (careful: aggressive denoise can distort consonants)



Make sure input is clean 16 kHz mono

Bad resampling / stereo phase weirdness from HDMI capture absolutely hurts ASR.