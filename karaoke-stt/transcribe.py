from rev_ai import apiclient
from rev_ai.models.asynchronous.job_status import JobStatus
import time
import pyaudio
import wave
import threading
from typing import *


token = "02mq7zrp5cOEKStOjfr2-yt_K21aBr4mJVnvLkcpsrK8I7EOKVz7Qh6KI6EI8YSL_tKXy2OaVKjhhr7x41AalUQ9hpkTk"


class Transcriber:
    def __init__(self, on_finish: Callable, on_error: Callable):
        self.transcript = []
        self.job = None
        self.stream = None
        self._record = False
        self.client = apiclient.RevAiAPIClient(token)
        self.lock = threading.Lock()
        self.on_finish = on_finish
        self.on_error = on_error

    @property
    def is_transcribing(self):
        return (self.job is not None
                and self.client.get_job_details(self.job.id).status == JobStatus.IN_PROGRESS)

    @property
    def is_recording(self):
        return self._record
    
    def start(self,
              chunk=1024,
              sample_format=pyaudio.paInt16,
              channels=2,
              rate=44100):
        if self.is_recording():
            raise RuntimeError("Already recording")
        def loop():
            self.lock.acquire()
            self._record = True
            p = pyaudio.PyAudio()
            self.stream = p.open(format=sample_format,
                                 channels=channels,
                                 rate=rate,
                                 frames_per_buffer=chunk,
                                 input=True)
            frames = []
            while self._record:
                data = self.stream.read(chunk)
                frames.append(data)
            self.stream.stop_stream()
            self.stream.close()
            p.terminate()
            filename = f"/tmp/{time.time()}.wav"
            wf = wave.open(filename, 'wb')
            wf.setnchannels(channels)
            wf.setsampwidth(p.get_sample_size(sample_format))
            wf.setframerate(rate)
            wf.writeframes(b''.join(frames))
            wf.close()
            # now transcribe it!
            self.job = self.client.submit_job_local_file(filename)
            while self.client.get_job_details(self.job.id).status == JobStatus.IN_PROGRESS:
                time.sleep(0.5)
            job_status = self.client.get_job_details(self.job.id).status
            if job_status == JobStatus.TRANSCRIBED:
                self.on_finish(self.client.get_transcript_text(self.job.id))
            else:
                self.on_error(self.job)
            self.lock.release()
        threading.Thread(target=loop).start()
    
    def stop(self):
        if not self._record:
            raise RuntimeError("Not recording")
        self._record = False


if __name__ == "__main__":
    # FIXME - replace this with a GUI
    t = Transcriber(
        on_finish=lambda txt: print(f"Got text: {txt}"),
        on_error=lambda job: print(f"Job {job.id} failed with status {job.status}")
    )
    t.start()
    time.sleep(2)
    t.stop()
    time.sleep(2)
    t.start()
    time.sleep(2)
    t.stop()