import subprocess, sys

url = "https://www.youtube.com/playlist?list=PLd7-bHaQwnthaNDpZ32TtYONGVk95-fhF"
cmd = [
    sys.executable, "-m", "yt_dlp",
    "--flat-playlist", "--playlist-end", "5",
    "--print", "%(id)s\t%(title)s\t%(duration)s\t%(upload_date)s",
    url,
]

print("CMD:", " ".join(cmd))
r = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                   encoding="utf-8", errors="replace")
print(f"rc={r.returncode}")
out = r.stdout.encode('ascii', errors='replace').decode('ascii')
print(f"stdout [{len(r.stdout)}]:")
print(out[:500])
err = r.stderr.encode('ascii', errors='replace').decode('ascii')
print(f"stderr [{len(r.stderr)}]:")
print(err[-500:])
