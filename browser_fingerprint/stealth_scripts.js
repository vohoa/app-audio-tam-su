/**
 * Browser Anti-Detection Stealth Scripts
 * 
 * JavaScript injection để bypass browser fingerprinting và bot detection.
 * Các scripts này sẽ được inject vào mọi page load.
 * 
 * Features:
 * - Canvas fingerprinting protection với noise injection
 * - WebGL fingerprinting spoofing
 * - WebRTC blocking để tránh IP leak
 * - Audio context fingerprinting protection
 * - Navigator properties overriding
 * - Plugin detection evasion
 */

(function() {
    'use strict';
    
    // ========================================
    // CANVAS FINGERPRINTING PROTECTION
    // ========================================
    
    /**
     * Thêm noise vào canvas để mỗi lần render có kết quả khác nhau
     * nhưng vẫn giống nhau với mắt thường (invisible noise)
     */
    const injectCanvasNoise = () => {
        // Lưu original methods
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        const originalToBlob = HTMLCanvasElement.prototype.toBlob;
        const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;
        
        // Generate consistent noise seed for this session
        const noiseSeed = Math.random();
        
        const addNoise = (imageData) => {
            const data = imageData.data;
            // Chỉ thêm noise nhẹ (±1-2 pixels) để không ảnh hưởng visual
            for (let i = 0; i < data.length; i += 4) {
                // Red, Green, Blue channels
                const noise = Math.floor((Math.random() - 0.5 + noiseSeed) * 2);
                data[i] = Math.max(0, Math.min(255, data[i] + noise));
                data[i+1] = Math.max(0, Math.min(255, data[i+1] + noise));
                data[i+2] = Math.max(0, Math.min(255, data[i+2] + noise));
                // Alpha channel không đổi
            }
            return imageData;
        };
        
        // Override toDataURL
        HTMLCanvasElement.prototype.toDataURL = function(type) {
            const context = this.getContext('2d');
            if (context) {
                const imageData = context.getImageData(0, 0, this.width, this.height);
                const noisyData = addNoise(imageData);
                context.putImageData(noisyData, 0, 0);
            }
            return originalToDataURL.apply(this, arguments);
        };
        
        // Override toBlob
        HTMLCanvasElement.prototype.toBlob = function(callback, type, quality) {
            const context = this.getContext('2d');
            if (context) {
                const imageData = context.getImageData(0, 0, this.width, this.height);
                const noisyData = addNoise(imageData);
                context.putImageData(noisyData, 0, 0);
            }
            return originalToBlob.apply(this, arguments);
        };
        
        // Override getImageData
        CanvasRenderingContext2D.prototype.getImageData = function() {
            const imageData = originalGetImageData.apply(this, arguments);
            return addNoise(imageData);
        };
        
        console.log('🎨 Canvas noise protection: ACTIVE');
    };
    
    // ========================================
    // WEBGL FINGERPRINTING SPOOFING
    // ========================================
    
    /**
     * Spoof WebGL vendor and renderer để tạo fingerprint khác biệt
     * Config sẽ được inject từ Python
     */
    const spoofWebGL = (vendor, renderer) => {
        const getParameterProxyHandler = {
            apply: function(target, thisArg, args) {
                const param = args[0];
                
                // UNMASKED_VENDOR_WEBGL
                if (param === 37445) {
                    return vendor || 'Google Inc. (NVIDIA)';
                }
                
                // UNMASKED_RENDERER_WEBGL
                if (param === 37446) {
                    return renderer || 'ANGLE (NVIDIA GeForce GTX 1660 Ti Direct3D11 vs_5_0 ps_5_0)';
                }
                
                return target.apply(thisArg, args);
            }
        };
        
        // Override WebGLRenderingContext
        const originalGetParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = new Proxy(
            originalGetParameter, 
            getParameterProxyHandler
        );
        
        // Override WebGL2RenderingContext
        if (window.WebGL2RenderingContext) {
            const originalGetParameter2 = WebGL2RenderingContext.prototype.getParameter;
            WebGL2RenderingContext.prototype.getParameter = new Proxy(
                originalGetParameter2, 
                getParameterProxyHandler
            );
        }
        
        console.log(`🎮 WebGL spoofing: ${vendor} / ${renderer}`);
    };
    
    // ========================================
    // WEBRTC BLOCKING (Prevent IP Leak)
    // ========================================
    
    /**
     * Block WebRTC để tránh leak địa chỉ IP thật
     */
    const blockWebRTC = () => {
        // Disable RTCPeerConnection
        if (window.RTCPeerConnection) {
            window.RTCPeerConnection = function() {
                throw new Error('WebRTC is disabled');
            };
        }
        
        if (window.webkitRTCPeerConnection) {
            window.webkitRTCPeerConnection = function() {
                throw new Error('WebRTC is disabled');
            };
        }
        
        if (window.mozRTCPeerConnection) {
            window.mozRTCPeerConnection = function() {
                throw new Error('WebRTC is disabled');
            };
        }
        
        // Disable getUserMedia
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            navigator.mediaDevices.getUserMedia = function() {
                return Promise.reject(new Error('Permission denied'));
            };
        }
        
        if (navigator.getUserMedia) {
            navigator.getUserMedia = function(constraints, success, error) {
                if (error) error(new Error('Permission denied'));
            };
        }
        
        console.log('🚫 WebRTC blocking: ACTIVE');
    };
    
    // ========================================
    // AUDIO CONTEXT FINGERPRINTING PROTECTION
    // ========================================
    
    /**
     * Thêm noise vào Audio Context để tránh fingerprinting
     */
    const injectAudioNoise = () => {
        const audioContexts = [window.AudioContext, window.webkitAudioContext];
        
        audioContexts.forEach(AudioContext => {
            if (!AudioContext) return;
            
            const OriginalAnalyser = AudioContext.prototype.createAnalyser;
            
            AudioContext.prototype.createAnalyser = function() {
                const analyser = OriginalAnalyser.call(this);
                
                const originalGetFloatFrequencyData = analyser.getFloatFrequencyData;
                analyser.getFloatFrequencyData = function(array) {
                    originalGetFloatFrequencyData.call(this, array);
                    // Add small noise
                    for (let i = 0; i < array.length; i++) {
                        array[i] += (Math.random() - 0.5) * 0.1;
                    }
                    return array;
                };
                
                const originalGetByteFrequencyData = analyser.getByteFrequencyData;
                analyser.getByteFrequencyData = function(array) {
                    originalGetByteFrequencyData.call(this, array);
                    // Add small noise
                    for (let i = 0; i < array.length; i++) {
                        array[i] += Math.floor((Math.random() - 0.5) * 2);
                    }
                    return array;
                };
                
                return analyser;
            };
        });
        
        console.log('🔊 Audio noise protection: ACTIVE');
    };
    
    // ========================================
    // NAVIGATOR PROPERTIES OVERRIDE
    // ========================================
    
    /**
     * Override navigator properties để match với fingerprint config
     * Config sẽ được inject từ Python
     */
    const overrideNavigator = (config) => {
        // Platform
        if (config.platform) {
            Object.defineProperty(navigator, 'platform', {
                get: () => config.platform
            });
        }
        
        // Language
        if (config.language) {
            Object.defineProperty(navigator, 'language', {
                get: () => config.language.split(',')[0]
            });
            
            Object.defineProperty(navigator, 'languages', {
                get: () => config.language.split(',').map(l => l.split(';')[0].trim())
            });
        }
        
        // Hardware concurrency (CPU cores)
        if (config.hardwareConcurrency) {
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => config.hardwareConcurrency
            });
        }
        
        // Device memory
        if (config.deviceMemory) {
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => config.deviceMemory
            });
        }
        
        // DoNotTrack
        if (config.doNotTrack) {
            Object.defineProperty(navigator, 'doNotTrack', {
                get: () => config.doNotTrack
            });
        }
        
        // Vendor
        Object.defineProperty(navigator, 'vendor', {
            get: () => 'Google Inc.'
        });
        
        console.log('🧭 Navigator override: ACTIVE', config);
    };
    
    // ========================================
    // SCREEN PROPERTIES OVERRIDE
    // ========================================
    
    /**
     * Override screen properties để match với fingerprint config
     */
    const overrideScreen = (config) => {
        if (!config) return;
        
        Object.defineProperty(screen, 'width', {
            get: () => config.width
        });
        
        Object.defineProperty(screen, 'height', {
            get: () => config.height
        });
        
        Object.defineProperty(screen, 'availWidth', {
            get: () => config.availWidth || config.width
        });
        
        Object.defineProperty(screen, 'availHeight', {
            get: () => config.availHeight || config.height - 40
        });
        
        Object.defineProperty(screen, 'colorDepth', {
            get: () => config.colorDepth || 24
        });
        
        Object.defineProperty(screen, 'pixelDepth', {
            get: () => config.pixelDepth || 24
        });
        
        console.log('🖥️ Screen override: ACTIVE', config);
    };
    
    // ========================================
    // PLUGIN DETECTION EVASION
    // ========================================
    
    /**
     * Spoof plugins để tránh bị detect là automation
     */
    const spoofPlugins = (pluginsList) => {
        if (!pluginsList || pluginsList.length === 0) return;
        
        // Create fake plugins
        const plugins = pluginsList.map((pluginData, index) => {
            return {
                name: pluginData.name,
                description: pluginData.description,
                filename: pluginData.filename,
                length: pluginData.mimeTypes ? pluginData.mimeTypes.length : 0,
                item: function(i) { return this[i]; },
                namedItem: function(name) { 
                    return this[name]; 
                }
            };
        });
        
        // Override navigator.plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => plugins
        });
        
        console.log('🔌 Plugins spoofing: ACTIVE', plugins.length + ' plugins');
    };
    
    // ========================================
    // TIMEZONE OVERRIDE
    // ========================================
    
    /**
     * Override timezone để match với config
     */
    const overrideTimezone = (timezone) => {
        if (!timezone) return;
        
        // Override Date.prototype.getTimezoneOffset
        const originalGetTimezoneOffset = Date.prototype.getTimezoneOffset;
        
        // Calculate offset for target timezone (simplified)
        const timezoneOffsets = {
            'Asia/Ho_Chi_Minh': -420,  // UTC+7
            'Asia/Bangkok': -420,
            'Asia/Singapore': -480,     // UTC+8
            'Asia/Manila': -480,
            'Asia/Jakarta': -420,
            'Asia/Tokyo': -540,         // UTC+9
            'Asia/Seoul': -540,
            'Asia/Hong_Kong': -480,
            'Asia/Taipei': -480,
        };
        
        const offset = timezoneOffsets[timezone] || 0;
        
        Date.prototype.getTimezoneOffset = function() {
            return offset;
        };
        
        // Override Intl.DateTimeFormat
        if (window.Intl && window.Intl.DateTimeFormat) {
            const OriginalDateTimeFormat = window.Intl.DateTimeFormat;
            window.Intl.DateTimeFormat = function(...args) {
                if (args.length === 0 || !args[0]) {
                    args[0] = timezone;
                }
                return new OriginalDateTimeFormat(...args);
            };
            window.Intl.DateTimeFormat.prototype = OriginalDateTimeFormat.prototype;
        }
        
        console.log('🌍 Timezone override: ' + timezone);
    };
    
    // ========================================
    // GEOLOCATION OVERRIDE
    // ========================================
    
    /**
     * Override geolocation API
     */
    const overrideGeolocation = (coords) => {
        if (!coords || !navigator.geolocation) return;
        
        const position = {
            coords: {
                latitude: coords.latitude,
                longitude: coords.longitude,
                accuracy: coords.accuracy || 100,
                altitude: null,
                altitudeAccuracy: null,
                heading: null,
                speed: null
            },
            timestamp: Date.now()
        };
        
        navigator.geolocation.getCurrentPosition = function(success, error) {
            if (success) success(position);
        };
        
        navigator.geolocation.watchPosition = function(success, error) {
            if (success) success(position);
            return 1;
        };
        
        console.log('📍 Geolocation override: ACTIVE', coords);
    };
    
    // ========================================
    // BATTERY API SPOOFING
    // ========================================
    
    /**
     * Spoof Battery API để tạo fingerprint khác biệt
     */
    const spoofBattery = () => {
        if (!navigator.getBattery) return;
        
        const fakeBattery = {
            charging: true,
            chargingTime: 0,
            dischargingTime: Infinity,
            level: 1.0,
            addEventListener: function() {},
            removeEventListener: function() {}
        };
        
        navigator.getBattery = function() {
            return Promise.resolve(fakeBattery);
        };
        
        console.log('🔋 Battery API spoofing: ACTIVE');
    };
    
    // ========================================
    // INITIALIZATION
    // ========================================
    
    /**
     * Main initialization function
     * Config sẽ được inject từ Python khi apply fingerprint
     */
    window.initStealthMode = function(fingerprintConfig) {
        console.log('🛡️ Initializing Stealth Mode...');
        console.log('📋 Fingerprint Config:', fingerprintConfig);
        
        try {
            // Always apply canvas protection
            injectCanvasNoise();
            
            // Always apply audio protection
            injectAudioNoise();
            
            // Always block WebRTC
            blockWebRTC();
            
            // Apply WebGL spoofing if config provided
            if (fingerprintConfig && fingerprintConfig.webgl) {
                spoofWebGL(
                    fingerprintConfig.webgl.vendor, 
                    fingerprintConfig.webgl.renderer
                );
            }
            
            // Apply navigator overrides
            if (fingerprintConfig) {
                const navConfig = {
                    platform: fingerprintConfig.platform,
                    language: fingerprintConfig.language,
                    hardwareConcurrency: fingerprintConfig.hardware ? fingerprintConfig.hardware.cpu_cores : undefined,
                    deviceMemory: fingerprintConfig.hardware ? fingerprintConfig.hardware.device_memory_gb : undefined,
                    doNotTrack: fingerprintConfig.do_not_track
                };
                overrideNavigator(navConfig);
            }
            
            // Apply screen overrides
            if (fingerprintConfig && fingerprintConfig.screen) {
                overrideScreen(fingerprintConfig.screen);
            }
            
            // Apply timezone override
            if (fingerprintConfig && fingerprintConfig.timezone) {
                overrideTimezone(fingerprintConfig.timezone);
            }
            
            // Apply geolocation override
            if (fingerprintConfig && fingerprintConfig.geolocation) {
                overrideGeolocation(fingerprintConfig.geolocation);
            }
            
            // Apply plugins spoofing
            if (fingerprintConfig && fingerprintConfig.plugins) {
                spoofPlugins(fingerprintConfig.plugins);
            }
            
            // Spoof battery API
            spoofBattery();
            
            console.log('✅ Stealth Mode: FULLY ACTIVE');
            
        } catch (error) {
            console.error('❌ Stealth Mode Error:', error);
        }
    };
    
    // Auto-init with default protection if no config
    if (!window.fingerprintConfig) {
        console.log('🛡️ Auto-initializing basic stealth protections...');
        injectCanvasNoise();
        injectAudioNoise();
        blockWebRTC();
        spoofBattery();
    }
    
})();
