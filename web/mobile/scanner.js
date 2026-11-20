/**
 * PyClean Pro Mobile Companion - Camera QR Scanner Module
 * High-performance QR code scanner with:
 * - Native BarcodeDetector acceleration where available
 * - Embedded jsQR engine fallback
 * - Torch / Flashlight control
 * - Camera flip (environment <-> user)
 * - Gallery image scanning & manual text paste fallback
 */

(function (root, factory) {
  if (typeof module === 'object' && typeof module.exports === 'object') {
    module.exports = factory();
  } else if (typeof define === 'function' && define.amd) {
    define([], factory);
  } else {
    root.MobileScanner = factory();
  }
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  let _mediaStream = null;
  let _activeTrack = null;
  let _videoElement = null;
  let _canvasElement = null;
  let _canvasContext = null;
  let _animFrameId = null;
  let _isScanning = false;
  let _facingMode = 'environment';
  let _torchState = false;
  let _nativeDetector = null;
  let _onDetectedCallback = null;
  let _onErrorCallback = null;

  function isBarcodeDetectorSupported() {
    return typeof window !== 'undefined' && 'BarcodeDetector' in window;
  }

  async function initBarcodeDetector() {
    if (isBarcodeDetectorSupported()) {
      try {
        const formats = await window.BarcodeDetector.getSupportedFormats();
        if (formats.includes('qr_code')) {
          _nativeDetector = new window.BarcodeDetector({ formats: ['qr_code'] });
          return true;
        }
      } catch (e) {
        _nativeDetector = null;
      }
    }
    return false;
  }

  async function startScanning({ videoElement, canvasElement, onDetected, onError }) {
    if (_isScanning) {
      stopScanning();
    }

    _videoElement = videoElement;
    _canvasElement = canvasElement || document.createElement('canvas');
    _canvasContext = _canvasElement.getContext('2d', { willReadFrequently: true });
    _onDetectedCallback = onDetected;
    _onErrorCallback = onError;
    _torchState = false;

    await initBarcodeDetector();

    try {
      const constraints = {
        audio: false,
        video: {
          facingMode: { ideal: _facingMode },
          width: { ideal: 1280 },
          height: { ideal: 720 }
        }
      };

      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error("La API de cámara (getUserMedia) no está disponible en este navegador o contexto.");
      }

      _mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
      _videoElement.srcObject = _mediaStream;
      _videoElement.setAttribute('playsinline', 'true');
      _videoElement.muted = true;
      await _videoElement.play();

      const videoTracks = _mediaStream.getVideoTracks();
      if (videoTracks.length > 0) {
        _activeTrack = videoTracks[0];
      }

      _isScanning = true;
      requestScanFrame();
      return true;
    } catch (err) {
      console.warn("Error al acceder a la cámara:", err);
      if (_onErrorCallback) {
        _onErrorCallback(err);
      }
      return false;
    }
  }

  function stopScanning() {
    _isScanning = false;
    if (_animFrameId) {
      cancelAnimationFrame(_animFrameId);
      _animFrameId = null;
    }

    if (_activeTrack) {
      try {
        if (_torchState) {
          _activeTrack.applyConstraints({ advanced: [{ torch: false }] }).catch(() => {});
        }
        _activeTrack.stop();
      } catch (e) {}
      _activeTrack = null;
    }

    if (_mediaStream) {
      _mediaStream.getTracks().forEach(track => {
        try { track.stop(); } catch (e) {}
      });
      _mediaStream = null;
    }

    if (_videoElement) {
      try {
        _videoElement.pause();
        _videoElement.srcObject = null;
      } catch (e) {}
    }
  }

  function requestScanFrame() {
    if (!_isScanning) return;
    _animFrameId = requestAnimationFrame(scanTick);
  }

  async function scanTick() {
    if (!_isScanning || !_videoElement) return;

    if (_videoElement.readyState === _videoElement.HAVE_ENOUGH_DATA) {
      const vWidth = _videoElement.videoWidth;
      const vHeight = _videoElement.videoHeight;

      if (vWidth > 0 && vHeight > 0) {
        let detected = false;

        // Intentar BarcodeDetector nativo primero
        if (_nativeDetector) {
          try {
            const barcodes = await _nativeDetector.detect(_videoElement);
            if (barcodes && barcodes.length > 0 && barcodes[0].rawValue) {
              handleDetection(barcodes[0].rawValue);
              detected = true;
            }
          } catch (e) {
            // Si el detector nativo falla, continuar al fallback jsQR
          }
        }

        // Fallback a jsQR
        if (!detected && typeof root.jsQR === 'function') {
          if (_canvasElement.width !== vWidth || _canvasElement.height !== vHeight) {
            _canvasElement.width = vWidth;
            _canvasElement.height = vHeight;
          }
          _canvasContext.drawImage(_videoElement, 0, 0, vWidth, vHeight);
          const imageData = _canvasContext.getImageData(0, 0, vWidth, vHeight);
          const code = root.jsQR(imageData.data, imageData.width, imageData.height, {
            inversionAttempts: 'dontInvert'
          });

          if (code && code.data) {
            handleDetection(code.data);
            detected = true;
          }
        }

        if (detected) {
          // Pausar unos ms tras detección para evitar disparos repetidos
          setTimeout(() => {
            if (_isScanning) requestScanFrame();
          }, 600);
          return;
        }
      }
    }

    requestScanFrame();
  }

  function handleDetection(data) {
    if (typeof navigator !== 'undefined' && navigator.vibrate) {
      try {
        navigator.vibrate([30, 50, 30]);
      } catch (e) {}
    }

    if (_onDetectedCallback) {
      _onDetectedCallback(data);
    }
  }

  async function flipCamera() {
    _facingMode = _facingMode === 'environment' ? 'user' : 'environment';
    if (_isScanning) {
      return await startScanning({
        videoElement: _videoElement,
        canvasElement: _canvasElement,
        onDetected: _onDetectedCallback,
        onError: _onErrorCallback
      });
    }
    return true;
  }

  async function toggleTorch() {
    if (!_activeTrack) return false;
    try {
      const capabilities = _activeTrack.getCapabilities ? _activeTrack.getCapabilities() : {};
      if (!capabilities.torch) {
        return false;
      }
      _torchState = !_torchState;
      await _activeTrack.applyConstraints({
        advanced: [{ torch: _torchState }]
      });
      return _torchState;
    } catch (e) {
      console.warn("Torch no soportado o error:", e);
      return false;
    }
  }

  function hasTorchCapability() {
    if (!_activeTrack || !_activeTrack.getCapabilities) return false;
    try {
      return !!_activeTrack.getCapabilities().torch;
    } catch (e) {
      return false;
    }
  }

  async function scanImageFile(file) {
    return new Promise((resolve, reject) => {
      if (!file) {
        return reject(new Error("No se ha seleccionado ningún archivo de imagen."));
      }

      const reader = new FileReader();
      reader.onload = async (e) => {
        const img = new Image();
        img.onload = async () => {
          // 1. Intentar BarcodeDetector si está disponible
          if (isBarcodeDetectorSupported()) {
            try {
              const detector = new window.BarcodeDetector({ formats: ['qr_code'] });
              const barcodes = await detector.detect(img);
              if (barcodes && barcodes.length > 0 && barcodes[0].rawValue) {
                return resolve(barcodes[0].rawValue);
              }
            } catch (err) {}
          }

          // 2. Fallback a jsQR
          const canvas = document.createElement('canvas');
          canvas.width = img.width;
          canvas.height = img.height;
          const ctx = canvas.getContext('2d', { willReadFrequently: true });
          ctx.drawImage(img, 0, 0);
          const imgData = ctx.getImageData(0, 0, img.width, img.height);

          if (typeof root.jsQR === 'function') {
            const qr = root.jsQR(imgData.data, imgData.width, imgData.height, {
              inversionAttempts: 'attemptBoth'
            });
            if (qr && qr.data) {
              return resolve(qr.data);
            }
          }

          reject(new Error("No se pudo detectar ningún código QR en la imagen proporcionada."));
        };
        img.onerror = () => reject(new Error("Error al decodificar la imagen."));
        img.src = e.target.result;
      };
      reader.onerror = () => reject(new Error("Error al leer el archivo."));
      reader.readAsDataURL(file);
    });
  }

  return {
    startScanning,
    stopScanning,
    flipCamera,
    toggleTorch,
    hasTorchCapability,
    scanImageFile,
    isBarcodeDetectorSupported,
    getFacingMode: () => _facingMode,
    isScanning: () => _isScanning
  };
});
