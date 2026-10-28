/* Video upload page: pick / drag and drop, validate, preview locally.
   Not sent to the server yet because the backend has no upload endpoint. */
(function () {
  'use strict';

  var MAX_MB = 200;

  var dz = document.getElementById('dropzone');
  var input = document.getElementById('video-input');
  var preview = document.getElementById('video-preview');
  var player = document.getElementById('video-player');
  var nameEl = document.getElementById('video-name');
  var sizeEl = document.getElementById('video-size');
  var errEl = document.getElementById('video-error');
  var removeBtn = document.getElementById('video-remove');
  var objectUrl = null;

  function showError(msg) {
    errEl.textContent = msg;
    errEl.hidden = !msg;
  }

  function fmtSize(bytes) {
    return bytes >= 1048576 ? (bytes / 1048576).toFixed(1) + ' MB' : Math.max(1, Math.round(bytes / 1024)) + ' KB';
  }

  function clearVideo() {
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    objectUrl = null;
    player.removeAttribute('src');
    player.load();
    preview.hidden = true;
    dz.hidden = false;
    input.value = '';
    showError('');
  }

  function handleFile(file) {
    showError('');
    if (!file) return;
    if (!/^video\//.test(file.type)) {
      showError('This file is not a video. Please choose an MP4, MOV or WebM file.');
      return;
    }
    if (file.size > MAX_MB * 1048576) {
      showError('The video is ' + fmtSize(file.size) + ', which exceeds the ' + MAX_MB + ' MB limit.');
      return;
    }
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    objectUrl = URL.createObjectURL(file);
    player.src = objectUrl;
    nameEl.textContent = file.name;
    sizeEl.textContent = ' · ' + fmtSize(file.size);
    dz.hidden = true;
    preview.hidden = false;
  }

  dz.addEventListener('click', function () { input.click(); });
  dz.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); input.click(); }
  });
  input.addEventListener('change', function () { handleFile(input.files[0]); });

  ['dragenter', 'dragover'].forEach(function (ev) {
    dz.addEventListener(ev, function (e) { e.preventDefault(); dz.classList.add('drag'); });
  });
  ['dragleave', 'drop'].forEach(function (ev) {
    dz.addEventListener(ev, function (e) { e.preventDefault(); dz.classList.remove('drag'); });
  });
  dz.addEventListener('drop', function (e) {
    handleFile(e.dataTransfer && e.dataTransfer.files[0]);
  });

  removeBtn.addEventListener('click', clearVideo);

  // Future hook: enable the "Analyze" button and send the file with FormData to the upload endpoint once the backend is ready.
})();