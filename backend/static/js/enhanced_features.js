/**
 * Enhanced Features for SaralPolicy
 * Audio controls, copy functionality, progress indicators, and more
 */

// Global audio controller
const AudioController = {
    audioElement: null,
    currentAudioUrl: null,
    isPlaying: false,
    
    async play(text, language) {
        try {
            // Show loading indicator
            this.showTTSLoading(true);
            
            // Stop any existing audio
            this.stop();
            
            const response = await fetch('/tts/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: text, language: language })
            });

            if (response.ok) {
                const result = await response.json();
                this.currentAudioUrl = result.audio_url;
                this.audioElement = new Audio(result.audio_url);
                
                // Add event listeners
                this.audioElement.onplay = () => {
                    this.isPlaying = true;
                    this.updatePlayButton(true);
                };
                
                this.audioElement.onpause = () => {
                    this.isPlaying = false;
                    this.updatePlayButton(false);
                };
                
                this.audioElement.onended = () => {
                    this.isPlaying = false;
                    this.updatePlayButton(false);
                };
                
                await this.audioElement.play();
                this.showTTSLoading(false);
            } else {
                // Fallback to browser TTS
                this.useBrowserTTS(text, language);
                this.showTTSLoading(false);
            }
        } catch (error) {
            console.error('TTS Error:', error);
            this.useBrowserTTS(text, language);
            this.showTTSLoading(false);
        }
    },
    
    pause() {
        if (this.audioElement && this.isPlaying) {
            this.audioElement.pause();
        }
    },
    
    resume() {
        if (this.audioElement && !this.isPlaying) {
            this.audioElement.play();
        }
    },
    
    stop() {
        if (this.audioElement) {
            this.audioElement.pause();
            this.audioElement.currentTime = 0;
            this.audioElement = null;
            this.isPlaying = false;
            this.updatePlayButton(false);
        }
    },
    
    download() {
        if (this.currentAudioUrl) {
            const a = document.createElement('a');
            a.href = this.currentAudioUrl;
            a.download = `policy_audio_${Date.now()}.mp3`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }
    },
    
    useBrowserTTS(text, language) {
        try {
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = language === 'hi' ? 'hi-IN' : 'en-US';
            speechSynthesis.speak(utterance);
        } catch (e) {
            alert('Text-to-speech is not available on this device.');
        }
    },
    
    updatePlayButton(isPlaying) {
        // Update UI button state
        const buttons = document.querySelectorAll('.audio-control-btn');
        buttons.forEach(btn => {
            if (btn.classList.contains('pause-btn')) {
                btn.style.display = isPlaying ? 'inline-flex' : 'none';
            }
            if (btn.classList.contains('play-btn')) {
                btn.style.display = isPlaying ? 'none' : 'inline-flex';
            }
        });
    },
    
    showTTSLoading(show) {
        const loaders = document.querySelectorAll('.tts-loading');
        loaders.forEach(loader => {
            loader.style.display = show ? 'inline-block' : 'none';
        });
    }
};

// Copy to clipboard functionality
const CopyController = {
    async copy(text, buttonElement) {
        try {
            await navigator.clipboard.writeText(text);
            this.showCopySuccess(buttonElement);
        } catch (error) {
            // Fallback for older browsers
            this.copyFallback(text, buttonElement);
        }
    },
    
    copyFallback(text, buttonElement) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        document.body.appendChild(textArea);
        textArea.select();
        
        try {
            document.execCommand('copy');
            this.showCopySuccess(buttonElement);
        } catch (error) {
            alert('Failed to copy to clipboard');
        }
        
        document.body.removeChild(textArea);
    },
    
    showCopySuccess(buttonElement) {
        const originalHTML = buttonElement.innerHTML;
        buttonElement.innerHTML = '<span class="material-icons">check</span> Copied!';
        buttonElement.style.background = '#198754';
        
        setTimeout(() => {
            buttonElement.innerHTML = originalHTML;
            buttonElement.style.background = '';
        }, 2000);
    }
};

// Progress indicator for analysis
const ProgressController = {
    steps: [
        { id: 1, text: 'Uploading document...', progress: 20 },
        { id: 2, text: 'Extracting text...', progress: 40 },
        { id: 3, text: 'Analyzing policy...', progress: 60 },
        { id: 4, text: 'Generating summary...', progress: 80 },
        { id: 5, text: 'Finalizing results...', progress: 100 }
    ],
    currentStep: 0,
    
    show() {
        const progressHTML = `
            <div id="analysisProgress" class="analysis-progress">
                <div class="progress-steps">
                    ${this.steps.map(step => `
                        <div class="progress-step" data-step="${step.id}">
                            <div class="step-icon">
                                <span class="material-icons">hourglass_empty</span>
                            </div>
                            <div class="step-text">${step.text}</div>
                        </div>
                    `).join('')}
                </div>
                <div class="progress-bar-container">
                    <div class="progress-bar-fill" id="progressBarFill"></div>
                </div>
                <div class="progress-percentage" id="progressPercentage">0%</div>
            </div>
        `;
        
        document.getElementById('loading').innerHTML = progressHTML;
    },
    
    async advance(stepId) {
        const step = this.steps.find(s => s.id === stepId);
        if (!step) return;
        
        this.currentStep = stepId;
        
        // Update step status
        const stepElement = document.querySelector(`[data-step="${stepId}"]`);
        if (stepElement) {
            stepElement.classList.add('active');
            const icon = stepElement.querySelector('.material-icons');
            if (stepId === this.steps.length) {
                icon.textContent = 'check_circle';
                stepElement.classList.add('complete');
            } else {
                icon.textContent = 'hourglass_top';
            }
        }
        
        // Update progress bar
        const progressBar = document.getElementById('progressBarFill');
        const progressText = document.getElementById('progressPercentage');
        
        if (progressBar && progressText) {
            progressBar.style.width = `${step.progress}%`;
            progressText.textContent = `${step.progress}%`;
        }
        
        // Mark previous steps as complete
        for (let i = 1; i < stepId; i++) {
            const prevStep = document.querySelector(`[data-step="${i}"]`);
            if (prevStep) {
                prevStep.classList.add('complete');
                const icon = prevStep.querySelector('.material-icons');
                icon.textContent = 'check_circle';
            }
        }
    },
    
    async simulateProgress(duration = 5000) {
        const stepDuration = duration / this.steps.length;
        
        for (let i = 1; i <= this.steps.length; i++) {
            await this.advance(i);
            if (i < this.steps.length) {
                await new Promise(resolve => setTimeout(resolve, stepDuration));
            }
        }
    },
    
    reset() {
        this.currentStep = 0;
    }
};

// Print functionality
const PrintController = {
    print() {
        window.print();
    },
    
    generatePrintView() {
        // Create print-specific styles if needed
        const printStyles = `
            @media print {
                .no-print { display: none !important; }
                .header { background: white !important; color: black !important; }
                .result-card { page-break-inside: avoid; }
            }
        `;
        
        const styleElement = document.createElement('style');
        styleElement.textContent = printStyles;
        document.head.appendChild(styleElement);
    }
};

// Share functionality (privacy-safe)
const ShareController = {
    async share(analysisData) {
        const shareText = this.generateShareText(analysisData);
        
        if (navigator.share) {
            try {
                await navigator.share({
                    title: 'Policy Analysis Summary',
                    text: shareText
                });
            } catch (error) {
                if (error.name !== 'AbortError') {
                    this.fallbackShare(shareText);
                }
            }
        } else {
            this.fallbackShare(shareText);
        }
    },
    
    generateShareText(analysisData) {
        // Remove PII and generate summary
        let shareText = '📄 Policy Analysis Summary\n\n';
        
        if (analysisData.summary) {
            shareText += `Summary: ${analysisData.summary.substring(0, 200)}...\n\n`;
        }
        
        if (analysisData.coverage) {
            shareText += 'Coverage Details:\n';
            for (const [key, value] of Object.entries(analysisData.coverage)) {
                shareText += `- ${key}: ${value}\n`;
            }
        }
        
        shareText += '\n✨ Analyzed with SaralPolicy';
        
        return shareText;
    },
    
    fallbackShare(text) {
        CopyController.copy(text, event.target);
    }
};

// Dark mode controller
const DarkModeController = {
    init() {
        const savedMode = localStorage.getItem('darkMode');
        if (savedMode === 'enabled') {
            this.enable();
        }
    },
    
    toggle() {
        const isDark = document.body.classList.contains('dark-mode');
        if (isDark) {
            this.disable();
        } else {
            this.enable();
        }
    },
    
    enable() {
        document.body.classList.add('dark-mode');
        localStorage.setItem('darkMode', 'enabled');
        this.updateToggleButton(true);
    },
    
    disable() {
        document.body.classList.remove('dark-mode');
        localStorage.setItem('darkMode', 'disabled');
        this.updateToggleButton(false);
    },
    
    updateToggleButton(isDark) {
        const button = document.getElementById('darkModeToggle');
        if (button) {
            const icon = button.querySelector('.material-icons');
            icon.textContent = isDark ? 'light_mode' : 'dark_mode';
        }
    }
};

// Error handler with better messages
const ErrorHandler = {
    show(error, context = 'general') {
        const errorMessages = {
            network: {
                title: 'Connection Error',
                message: 'Unable to connect to the server. Please check your internet connection and try again.',
                action: 'Retry'
            },
            fileSize: {
                title: 'File Too Large',
                message: 'The file you selected is too large. Please choose a file smaller than 10MB.',
                action: 'Choose Another File'
            },
            fileType: {
                title: 'Unsupported File Type',
                message: 'Please upload a PDF, DOCX, or TXT file.',
                action: 'Choose Another File'
            },
            analysis: {
                title: 'Analysis Failed',
                message: 'We couldn\'t analyze this document. Please make sure it\'s a valid insurance policy.',
                action: 'Try Another Document'
            },
            tts: {
                title: 'Audio Not Available',
                message: 'Text-to-speech is not available on this device. You can still read the analysis.',
                action: 'Continue'
            }
        };
        
        const errorConfig = errorMessages[context] || {
            title: 'Error',
            message: error.message || 'Something went wrong. Please try again.',
            action: 'Retry'
        };
        
        this.display(errorConfig);
    },
    
    display(config) {
        const errorHTML = `
            <div class="error-card">
                <div class="error-icon">
                    <span class="material-icons">error_outline</span>
                </div>
                <div class="error-content">
                    <h3>${config.title}</h3>
                    <p>${config.message}</p>
                </div>
                <button class="btn error-action-btn" onclick="this.parentElement.remove()">
                    ${config.action}
                </button>
            </div>
        `;
        
        document.getElementById('resultsContent').innerHTML = errorHTML;
        document.getElementById('resultsSection').classList.add('show');
    }
};

// Export controllers for global access
window.AudioController = AudioController;
window.CopyController = CopyController;
window.ProgressController = ProgressController;
window.PrintController = PrintController;
window.ShareController = ShareController;
window.DarkModeController = DarkModeController;
window.ErrorHandler = ErrorHandler;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    DarkModeController.init();
    PrintController.generatePrintView();
});
