document.addEventListener('DOMContentLoaded', () => {
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    const previewContainer = document.getElementById('preview-container');
    const previewImage = document.getElementById('preview-image');
    const removeBtn = document.getElementById('remove-btn');
    const analyzeBtn = document.getElementById('analyze-btn');
    const resultsContainer = document.getElementById('results-container');
    const btnText = document.getElementById('btn-text');
    const loader = document.getElementById('loader');

    let currentFile = null;

    // Drag and Drop events
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        uploadArea.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, unhighlight, false);
    });

    function highlight(e) {
        uploadArea.classList.add('dragover');
    }

    function unhighlight(e) {
        uploadArea.classList.remove('dragover');
    }

    uploadArea.addEventListener('drop', handleDrop, false);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    }

    // Click to upload
    uploadArea.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', function () {
        handleFiles(this.files);
    });

    function handleFiles(files) {
        if (files.length > 0) {
            const file = files[0];
            if (file.type.startsWith('image/')) {
                currentFile = file;
                showPreview(file);
                analyzeBtn.disabled = false;
                resultsContainer.style.display = 'none';
            } else {
                alert('Please upload an image file (JPG/PNG).');
            }
        }
    }

    function showPreview(file) {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onloadend = function () {
            previewImage.src = reader.result;
            previewContainer.style.display = 'block';
            uploadArea.style.display = 'none';
        }
    }

    removeBtn.addEventListener('click', () => {
        currentFile = null;
        fileInput.value = '';
        previewContainer.style.display = 'none';
        uploadArea.style.display = 'block';
        analyzeBtn.disabled = true;
        resultsContainer.style.display = 'none';
    });

    analyzeBtn.addEventListener('click', async () => {
        if (!currentFile) return;

        // UI Loading State
        analyzeBtn.disabled = true;
        btnText.textContent = 'Analyzing...';
        loader.style.display = 'inline-block';
        resultsContainer.style.display = 'none';

        const formData = new FormData();
        formData.append('file', currentFile);

        try {
            const response = await fetch('/predict', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(await response.text());
            }

            const data = await response.json();
            displayResults(data);

        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred during analysis: ' + error.message);
        } finally {
            // Reset Button State
            analyzeBtn.disabled = false;
            btnText.textContent = 'Analyze Image';
            loader.style.display = 'none';
        }
    });

    function displayResults(data) {
        const predictionLabel = document.getElementById('prediction-label');
        const normalProb = document.getElementById('normal-prob');
        const pneuProb = document.getElementById('pneu-prob');
        const normalBar = document.getElementById('normal-bar');
        const pneuBar = document.getElementById('pneu-bar');

        // Update Text
        predictionLabel.textContent = data.prediction;

        // Set Color Class
        predictionLabel.className = 'prediction-label';
        if (data.prediction === 'NORMAL') {
            predictionLabel.classList.add('normal');
        } else {
            predictionLabel.classList.add('pneumonia');
        }

        const probNormal = (data.probabilities.NORMAL * 100).toFixed(1);
        const probPneu = (data.probabilities.PNEUMONIA * 100).toFixed(1);

        normalProb.textContent = probNormal + '%';
        pneuProb.textContent = probPneu + '%';

        // Animate Bars
        resultsContainer.style.display = 'block';

        // Small delay to allow display:block to render before animating width
        setTimeout(() => {
            normalBar.style.width = probNormal + '%';
            pneuBar.style.width = probPneu + '%';
        }, 50);
    }
});
