import React, { useState } from 'react';
import './AssignmentPage.css';

function AssignmentPage() {
  const [step, setStep] = useState('choice'); // choice, loading, results, error, edit
  const [method, setMethod] = useState(null); // 'manual' or 'excel'
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [fileName, setFileName] = useState(null);
  const [editedResults, setEditedResults] = useState(null);
  const [editMode, setEditMode] = useState(null); // null, 'select', or 'swap'

  const handleMethodChoice = async (selectedMethod) => {
    setMethod(selectedMethod);
    setError(null);

    if (selectedMethod === 'manual') {
      runManualAssignment();
    } else {
      setStep('file-upload');
    }
  };

  const runManualAssignment = async () => {
    setStep('loading');
    try {
      const response = await fetch('http://localhost:8000/api/run-assignment-manual', {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error('Failed to run manual assignment');
      }

      const data = await response.json();
      setResults(data.data);
      setEditedResults(JSON.parse(JSON.stringify(data.data))); // Deep copy
      setStep('results');
    } catch (err) {
      setError(err.message);
      setStep('error');
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
      setError('Please upload a valid Excel file (.xlsx or .xls)');
      return;
    }

    setStep('loading');
    setFileName(file.name);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:8000/api/run-assignment-excel', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to process Excel file');
      }

      const data = await response.json();
      setResults(data.data);
      setEditedResults(JSON.parse(JSON.stringify(data.data))); // Deep copy
      setStep('results');
    } catch (err) {
      setError(err.message);
      setStep('error');
    }
  };

  const handleBack = () => {
    setStep('choice');
    setMethod(null);
    setResults(null);
    setEditedResults(null);
    setError(null);
    setFileName(null);
    setEditMode(null);
  };

  const startEdit = (mode) => {
    setEditMode(mode);
    setStep('edit');
  };

  const cancelEdit = () => {
    setEditedResults(JSON.parse(JSON.stringify(results)));
    setEditMode(null);
    setStep('results');
  };

  const saveEdits = () => {
    setResults(JSON.parse(JSON.stringify(editedResults)));
    setEditMode(null);
    setStep('results');
  };

  const removeTA = (professor, ta) => {
    if (!editedResults) return;
    setEditedResults(prev => ({
      ...prev,
      assignments: {
        ...prev.assignments,
        [professor]: prev.assignments[professor].filter(t => t !== ta)
      },
      workloads: {
        ...prev.workloads,
        [ta]: Math.max(0, prev.workloads[ta] - 1)
      }
    }));
  };

  const addTA = (professor, ta) => {
    if (!editedResults) return;
    if (editedResults.assignments[professor].includes(ta)) return;
    setEditedResults(prev => ({
      ...prev,
      assignments: {
        ...prev.assignments,
        [professor]: [...prev.assignments[professor], ta]
      },
      workloads: {
        ...prev.workloads,
        [ta]: prev.workloads[ta] + 1
      }
    }));
  };

  return (
    <div className="assignment-page">
      {step === 'choice' && <ChoiceView onMethodChoice={handleMethodChoice} />}
      {step === 'file-upload' && (
        <FileUploadView onFileUpload={handleFileUpload} onBack={handleBack} />
      )}
      {step === 'loading' && <LoadingView method={method} fileName={fileName} />}
      {step === 'results' && (
        <ResultsView
          results={editedResults || results}
          method={method}
          onBack={handleBack}
          onEdit={startEdit}
          hasChanges={JSON.stringify(results) !== JSON.stringify(editedResults)}
        />
      )}
      {step === 'edit' && (
        <EditView
          results={editedResults}
          mode={editMode}
          onRemoveTA={removeTA}
          onAddTA={addTA}
          onSave={saveEdits}
          onCancel={cancelEdit}
        />
      )}
      {step === 'error' && <ErrorView error={error} onBack={handleBack} />}
    </div>
  );
}

function ChoiceView({ onMethodChoice }) {
  return (
    <div className="choice-container">
      <div className="choice-content">
        <div className="choice-header">
          <h1>TA Assignment System</h1>
          <p className="subtitle">Select your preferred assignment method</p>
        </div>

        <div className="choice-cards">
          <div
            className="choice-card manual-card"
            onClick={() => onMethodChoice('manual')}
            role="button"
            tabIndex={0}
            onKeyPress={(e) => e.key === 'Enter' && onMethodChoice('manual')}
          >
            <div className="card-gradient-bg"></div>
            <div className="card-content">
              <div className="card-icon">👥</div>
              <h2>Manual Assignment</h2>
              <p>Use existing system data</p>
              <div className="card-features">
                <div className="feature">✓ Quick processing</div>
                <div className="feature">✓ System data</div>
              </div>
              <button className="card-btn">Select Method</button>
            </div>
          </div>

          <div className="divider">
            <span>or</span>
          </div>

          <div
            className="choice-card excel-card"
            onClick={() => onMethodChoice('excel')}
            role="button"
            tabIndex={0}
            onKeyPress={(e) => e.key === 'Enter' && onMethodChoice('excel')}
          >
            <div className="card-gradient-bg"></div>
            <div className="card-content">
              <div className="card-icon">📊</div>
              <h2>Excel Upload</h2>
              <p>Import custom Excel file</p>
              <div className="card-features">
                <div className="feature">✓ Custom data</div>
                <div className="feature">✓ Flexible format</div>
              </div>
              <button className="card-btn">Select Method</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function FileUploadView({ onFileUpload, onBack }) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const files = e.dataTransfer.files;
    if (files && files[0]) {
      setSelectedFile(files[0]);
      const event = { target: { files } };
      onFileUpload(event);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      onFileUpload(e);
    }
  };

  return (
    <div className="file-upload-container">
      <button className="nav-btn back-btn" onClick={onBack}>
        <span className="btn-icon">←</span> Back
      </button>

      <div className="upload-content">
        <h1>Upload Excel File</h1>
        <p className="subtitle">
          Upload your Excel file with TA and Professor information
        </p>

        <div
          className={`drop-zone ${dragActive ? 'active' : ''} ${selectedFile ? 'selected' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <div className="drop-zone-content">
            <div className="upload-icon">
              {selectedFile ? '✓' : '📁'}
            </div>
            {selectedFile ? (
              <>
                <p className="file-name">{selectedFile.name}</p>
                <p className="file-size">
                  {(selectedFile.size / 1024).toFixed(2)} KB
                </p>
              </>
            ) : (
              <>
                <p className="drop-text">Drag your Excel file here</p>
                <p className="or-text">or</p>
                <label className="file-input-label">
                  Browse Files
                  <input
                    type="file"
                    accept=".xlsx,.xls"
                    onChange={handleFileChange}
                    className="file-input"
                  />
                </label>
              </>
            )}
            <p className="file-format">.xlsx or .xls format</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function LoadingView({ method, fileName }) {
  return (
    <div className="loading-container">
      <div className="loading-content">
        <div className="spinner"></div>
        <h2>Processing Assignment</h2>
        <p className="loading-text">
          {method === 'manual'
            ? 'Running assignment algorithm...'
            : `Processing ${fileName}...`}
        </p>
        <div className="loading-bar-container">
          <div className="loading-bar"></div>
        </div>
      </div>
    </div>
  );
}

function ResultsView({ results, method, onBack, onEdit, hasChanges }) {
  if (!results || !results.assignments) {
    return (
      <div className="results-container">
        <button className="nav-btn back-btn" onClick={onBack}>
          <span className="btn-icon">←</span> Back
        </button>
        <h1>Results</h1>
        <p>No assignment data available</p>
      </div>
    );
  }

  const { assignments, workloads } = results;
  const sortedProfessors = Object.keys(assignments).sort();
  const sortedTAs = Object.keys(workloads).sort();
  const totalAssignments = Object.values(assignments).flat().length;
  const avgAssignments = (totalAssignments / sortedTAs.length).toFixed(2);
  const maxWorkload = Math.max(...Object.values(workloads), 1);

  return (
    <div className="results-container">
      <div className="results-header">
        <button className="nav-btn back-btn" onClick={onBack}>
          <span className="btn-icon">←</span> Back
        </button>
        <div>
          <h1>Assignment Results</h1>
          <p className="result-subtitle">
            {method === 'manual' ? 'Manual' : 'Excel-based'} assignment
            {hasChanges && ' (modified)'}
          </p>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-number">{totalAssignments}</div>
          <div className="stat-label">Total Assignments</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{sortedProfessors.length}</div>
          <div className="stat-label">Professors</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{sortedTAs.length}</div>
          <div className="stat-label">TAs Assigned</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{avgAssignments}</div>
          <div className="stat-label">Avg per TA</div>
        </div>
      </div>

      <div className="results-grid">
        <div className="results-section">
          <h2>Professor Assignments</h2>
          <div className="assignments-list">
            {sortedProfessors.map((professor) => (
              <div key={professor} className="assignment-item">
                <div className="item-header">
                  <h3>{professor}</h3>
                  <span className="badge">
                    {assignments[professor].length} TA
                    {assignments[professor].length !== 1 ? 's' : ''}
                  </span>
                </div>
                <div className="ta-tags">
                  {assignments[professor].length > 0 ? (
                    assignments[professor].map((ta) => (
                      <div key={ta} className="ta-tag">
                        {ta}
                      </div>
                    ))
                  ) : (
                    <div className="empty-state">No TAs assigned</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="results-section">
          <h2>TA Workload Distribution</h2>
          <div className="workload-list">
            {sortedTAs.map((ta) => (
              <div key={ta} className="workload-item">
                <div className="workload-header">
                  <h3>{ta}</h3>
                  <span className="workload-count">{workloads[ta]}</span>
                </div>
                <div className="workload-bar-wrapper">
                  <div className="workload-bar-bg">
                    <div
                      className="workload-bar-fill"
                      style={{
                        width: `${(workloads[ta] / maxWorkload) * 100}%`,
                      }}
                    ></div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="action-buttons">
        <button
          className="btn btn-primary"
          onClick={() => onEdit('select')}
        >
          ✏️ Edit Assignments
        </button>
        <button
          className="btn btn-secondary"
          onClick={() => exportResults(results)}
        >
          📥 Export as JSON
        </button>
        <button
          className="btn btn-outline"
          onClick={onBack}
        >
          🔄 New Assignment
        </button>
      </div>
    </div>
  );
}

function EditView({ results, mode, onRemoveTA, onAddTA, onSave, onCancel }) {
  const { assignments, workloads } = results;
  const sortedProfessors = Object.keys(assignments).sort();
  const sortedTAs = Object.keys(workloads).sort();
  const assignedTAs = new Set(Object.values(assignments).flat());
  const unassignedTAs = sortedTAs.filter(ta => !assignedTAs.has(ta));

  return (
    <div className="edit-container">
      <div className="edit-header">
        <h1>Edit Assignments</h1>
        <p>Customize the assignment by adding or removing TAs</p>
      </div>

      <div className="edit-mode-selector">
        <div className={`mode-badge ${mode === 'select' ? 'active' : ''}`}>
          ✏️ Edit Mode: Modify Assignments
        </div>
      </div>

      <div className="edit-grid">
        <div className="edit-section">
          <h2>Professor Assignments</h2>
          <div className="edit-assignments">
            {sortedProfessors.map((professor) => (
              <div key={professor} className="edit-prof-card">
                <h3>{professor}</h3>
                <div className="edit-ta-list">
                  {assignments[professor].map((ta) => (
                    <div key={ta} className="edit-ta-item">
                      <span>{ta}</span>
                      <button
                        className="remove-btn"
                        onClick={() => onRemoveTA(professor, ta)}
                        title="Remove TA"
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                </div>

                {unassignedTAs.length > 0 && (
                  <div className="add-ta-section">
                    <p className="add-ta-label">Add TA:</p>
                    <div className="add-ta-options">
                      {unassignedTAs.map((ta) => (
                        <button
                          key={ta}
                          className="add-ta-btn"
                          onClick={() => onAddTA(professor, ta)}
                        >
                          + {ta}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="edit-section">
          <h2>TA Workload Summary</h2>
          <div className="workload-summary">
            {sortedTAs.map((ta) => (
              <div key={ta} className="workload-summary-item">
                <div className="workload-name">{ta}</div>
                <div className="workload-badge">{workloads[ta]}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="edit-actions">
        <button className="btn btn-success" onClick={onSave}>
          ✓ Save Changes
        </button>
        <button className="btn btn-secondary" onClick={onCancel}>
          ✕ Cancel
        </button>
      </div>
    </div>
  );
}

function ErrorView({ error, onBack }) {
  return (
    <div className="error-container">
      <div className="error-content">
        <div className="error-icon">⚠️</div>
        <h2>Oops! Something went wrong</h2>
        <p className="error-message">{error}</p>
        <div className="error-suggestion">
          <p>Please try again or contact support if the issue persists.</p>
        </div>
      </div>
      <button className="btn btn-primary" onClick={onBack}>
        ← Try Again
      </button>
    </div>
  );
}

function exportResults(results) {
  const dataStr = JSON.stringify(results, null, 2);
  const dataBlob = new Blob([dataStr], { type: 'application/json' });
  const url = URL.createObjectURL(dataBlob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `assignment_results_${new Date().toISOString().split('T')[0]}.json`;
  link.click();
  URL.revokeObjectURL(url);
}

export default AssignmentPage;
