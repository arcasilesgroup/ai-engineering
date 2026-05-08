# FFmpeg Recipes

## Extract segment by timestamp

```bash
ffmpeg -i raw.mp4 -ss -to -c copy segment_01.mp4
```

## Batch cut from edit decision list

```bash
while IFS=, read -r start end label; do
  ffmpeg -i raw.mp4 -ss "$start" -to "$end" -c copy "segments/${label}.mp4"
done < cuts.txt
```

## Concatenate segments

```bash
for f in segments/*.mp4; do echo "file '$f'"; done > concat.txt
ffmpeg -f concat -safe 0 -i concat.txt -c copy assembled.mp4
```

## Common one-liners

```bash
# Proxy:    ffmpeg -i raw.mp4 -vf "scale=960:-2" -c:v libx264 -preset ultrafast -crf 28 proxy.mp4
# Audio:    ffmpeg -i raw.mp4 -vn -acodec pcm_s16le -ar 16000 audio.wav
# Normalize: ffmpeg -i seg.mp4 -af loudnorm=I=-16:TP=-1.5:LRA=11 -c:v copy normalized.mp4
# Scene:    ffmpeg -i input.mp4 -vf "select='gt(scene,0.3)',showinfo" -vsync vfr -f null - 2>&1 | grep showinfo
# Silence:  ffmpeg -i input.mp4 -af silencedetect=noise=-30dB:d=2 -f null - 2>&1 | grep silence
```
