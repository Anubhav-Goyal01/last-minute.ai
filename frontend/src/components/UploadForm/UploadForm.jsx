import { useState } from "react";
import styles from "./UploadForm.module.css"; // Import the CSS module

export const UploadForm = () => {
  const [files, setFiles] = useState([]); // To handle multiple files
  const [urls, setUrls] = useState([""]);

  const handleFileChange = (event) => {
    setFiles([...event.target.files]); // Collect all selected files
  };

  const handleUrlChange = (event, index) => {
    const newUrls = [...urls];
    newUrls[index] = event.target.value;
    setUrls(newUrls);
  };

  const handleAddUrl = () => {
    setUrls([...urls, ""]); // Add a new input for another URL
  };

  const handleSubmit = async () => {
    // Create a FormData object to hold the files
    const formData = new FormData();
    files.forEach((file) => {
      formData.append("files", file);
    });

    // Construct the JSON payload with URLs and document types
    const jsonPayload = {
      documents: urls, // Array of URLs
    };

    // Combine both formData and jsonPayload in the same request
    // This is typically done by appending the JSON payload as a Blob in formData
    formData.append("json", JSON.stringify(jsonPayload));

    try {
      // Make an asynchronous POST request to the backend
      const response = await fetch("http://127.0.0.1:5000/upload", {
        method: "POST",
        body: formData, // Body now contains both files and JSON payload
      });

      // Handle the response from the server
      const responseData = await response.json();
      if (response.ok) {
        console.log("Questions:", responseData);
        // Clear inputs after successful submission
        setFiles([]);
        setUrls([""]);
      } else {
        // Handle errors, such as showing a message to the user
        console.error("Error from server:", responseData.error);
      }
    } catch (error) {
      console.error("Submission failed:", error);
    }
  };

  return (
    <div className={styles.uploadFormContainer}>
      <h2>Upload Documents</h2>
      <input type="file" multiple accept=".pdf" onChange={handleFileChange} />
      <br />
      <br />
      {urls.map((url, index) => (
        <input
          key={index}
          type="text"
          placeholder="Enter YouTube URL"
          value={url}
          onChange={(event) => handleUrlChange(event, index)}
        />
      ))}
      <button onClick={handleAddUrl}>Add Another URL</button>
      <br />
      <br />
      <button onClick={handleSubmit}>Submit</button>
    </div>
  );
};
