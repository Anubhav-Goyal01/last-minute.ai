import React, { useState } from 'react';
import styles from './UploadForm.module.css'; // Import the CSS module

export const UploadForm = () => {
    const [file, setFile] = useState(null);
    const [url, setUrl] = useState('');

    const handleFileChange = (event) => {
        const selectedFile = event.target.files[0];
        setFile(selectedFile);
    };

    const handleUrlChange = (event) => {
        setUrl(event.target.value);
    };

    const handleSubmit = () => {
        // Send file and/or URL to backend
        console.log('File:', file);
        console.log('URL:', url);

        // Clear inputs after submission (optional)
        setFile(null);
        setUrl('');
    };

    return (
        <div className={styles.uploadFormContainer}>
            <h2>Upload Documents</h2>
            <input type="file" onChange={handleFileChange} />
            <br />
            <input type="text" placeholder="Enter Youtube URL" value={url} onChange={handleUrlChange} />
            <br />
            <button onClick={handleSubmit}>Submit</button>
        </div>
    );
};

