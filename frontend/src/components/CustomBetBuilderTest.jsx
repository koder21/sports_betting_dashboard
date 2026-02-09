import React from "react";
import "../styles/CustomBetBuilder.css";

function CustomBetBuilderTest({ isOpen, onClose }) {
  if (!isOpen) return null;

  console.log("Test modal rendered");

  return (
    <div className="custom-bet-builder-overlay" onClick={onClose}>
      <div
        className="custom-bet-builder-modal"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="builder-header">
          <h2>Test Modal</h2>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>
        <div className="builder-content">
          <p>If you see this, the modal is rendering correctly!</p>
          <button onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}

export default CustomBetBuilderTest;
