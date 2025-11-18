document.addEventListener("DOMContentLoaded", () => {
  const startBtn = document.getElementById("start-record-btn");
  const stopBtn = document.getElementById("stop-record-btn");
  const statusEl = document.getElementById("record-status");
  const audioPreview = document.getElementById("record-audio-preview");
  const uploadMessage = document.getElementById("upload-message");

  const fileForm = document.getElementById("file-upload-form");
  const fileInput = document.getElementById("file-input");

  function showMessage(text, ok) {
    uploadMessage.textContent = text;
    uploadMessage.style.display = "block";
    uploadMessage.className = "notice " + (ok ? "notice-ok" : "notice-error");
  }

  startBtn.addEventListener("click", async () => {
    try {
      await startRecording();
      statusEl.textContent = "Recording...";
      startBtn.disabled = true;
      stopBtn.disabled = false;
      audioPreview.style.display = "none";
    } catch (err) {
      console.error(err);
      showMessage("Could not start recording: " + err, false);
    }
  });

  stopBtn.addEventListener("click", () => {
    if (getRecordingState() === "recording") {
      statusEl.textContent = "Stopping...";
      stopBtn.disabled = true;
      stopRecording();
    }
  });

  document.addEventListener("recordingComplete", async (event) => {
    const blob = event.detail.blob;

    audioPreview.src = URL.createObjectURL(blob);
    audioPreview.style.display = "block";

    statusEl.textContent = "Uploading recording...";

    try {
      const response = await uploadRecording("/upload");
      const data = await response.json();

      if (data.error) {
        showMessage("Upload failed: " + data.error, false);
        statusEl.textContent = "Upload failed.";
      } else {
        showMessage("Recording uploaded successfully.", true);
        statusEl.textContent = "Upload complete.";
      }
    } catch (err) {
      console.error(err);
      showMessage("Upload failed: " + err, false);
    } finally {
      startBtn.disabled = false;
      stopBtn.disabled = true;
    }
  });

  fileForm.addEventListener("submit", (event) => {
    event.preventDefault();

    if (!fileInput.files.length) {
      showMessage("Please choose a file to upload.", false);
      return;
    }

    const formData = new FormData(fileForm);
    showMessage("Uploading file...", true);

    fetch("/upload", {
      method: "POST",
      body: formData
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.error) {
          showMessage("Upload failed: " + data.error, false);
        } else {
          showMessage("File uploaded successfully.", true);
          fileInput.value = "";
        }
      })
      .catch((err) => {
        console.error(err);
        showMessage("Upload failed: " + err, false);
      });
  });
});
