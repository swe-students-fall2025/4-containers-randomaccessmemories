// record.js - MediaRecorder audio capture

let mediaRecorder = null;
let audioChunks = [];
let audioBlob = null;
let audioStream = null;


async function startRecording() {
  try {
    audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    
    mediaRecorder = new MediaRecorder(audioStream);
    audioChunks = [];
    
    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunks.push(event.data);
      }
    };
    

    mediaRecorder.onstop = () => {
      audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
      
      if (audioStream) {
        audioStream.getTracks().forEach(track => track.stop());
      }
      
      const event = new CustomEvent('recordingComplete', { 
        detail: { blob: audioBlob } 
      });
      document.dispatchEvent(event);
    };
    
    mediaRecorder.start();
    
    return true;
  } catch (error) {
    console.error('Error starting recording:', error);
    throw error;
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
  }
}



function getRecordingState() {
  return mediaRecorder ? mediaRecorder.state : 'inactive';
}


function getAudioBlob() {
  return audioBlob;
}


function getAudioURL() {
  return audioBlob ? URL.createObjectURL(audioBlob) : null;
}

function downloadRecording(filename = 'recording.webm') {
  if (!audioBlob) {
    console.error('No recording available to download');
    return;
  }
  
  const url = URL.createObjectURL(audioBlob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}


async function uploadRecording(url, filename = 'recording.webm') {
  if (!audioBlob) {
    throw new Error('No recording available to upload');
  }
  
  const formData = new FormData();
  formData.append('file', audioBlob, filename);
  
  const response = await fetch(url, {
    method: 'POST',
    body: formData
  });
  
  return response;
}

function resetRecorder() {
  audioChunks = [];
  audioBlob = null;
  
  if (audioStream) {
    audioStream.getTracks().forEach(track => track.stop());
    audioStream = null;
  }
  
  mediaRecorder = null;
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    startRecording,
    stopRecording,
    getRecordingState,
    getAudioBlob,
    getAudioURL,
    downloadRecording,
    uploadRecording,
    resetRecorder
  };
}