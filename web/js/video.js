/* Trang upload video: chọn / kéo thả, kiểm tra, xem trước cục bộ.
   Chưa gửi lên server vì backend chưa có endpoint upload. */
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
      showError('Tệp này không phải video. Hãy chọn MP4, MOV hoặc WebM.');
      return;
    }
    if (file.size > MAX_MB * 1048576) {
      showError('Video nặng ' + fmtSize(file.size) + ', vượt giới hạn ' + MAX_MB + ' MB.');
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

  // Điểm nối sau này: bật nút "Phân tích" và gửi file bằng FormData tới endpoint upload khi backend sẵn sàng.
})();
