import React from 'react';
import { ChatWithYourData } from './components/ChatWithYourData/ChatWithYourData';
import { UploadForm } from './components/UploadForm/UploadForm';
import styles from './App.module.css'; // Import CSS module files

function App() {
  return (
     <div className={styles.container}>
      LastMinute.ai
       <div className={styles.left}>
         <UploadForm />
      </div>
      <div className={styles.right}>
        <ChatWithYourData />
      </div>
    </div>
  );
}

export default App;

