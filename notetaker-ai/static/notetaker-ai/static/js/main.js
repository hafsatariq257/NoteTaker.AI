// ─── Action item checkboxes ───
document.querySelectorAll('.action-item').forEach(item => {
  item.addEventListener('click', () => {
    const checkbox = item.querySelector('.checkbox')
    const text = item.querySelector('.action-text')
    checkbox.classList.toggle('checked')
    text.classList.toggle('done')
  })
})

// ─── Transcript toggle ───
const transcriptToggle = document.querySelector('.transcript-toggle')
const transcriptBody = document.querySelector('.transcript-body')

if (transcriptToggle && transcriptBody) {
  transcriptToggle.addEventListener('click', () => {
    transcriptBody.classList.toggle('open')
    const arrow = transcriptToggle.querySelector('.arrow')
    if (arrow) arrow.textContent = transcriptBody.classList.contains('open') ? 'Hide' : 'Show'
  })
}

// ─── File upload preview ───
const fileInput = document.querySelector('#audio_file')
const uploadArea = document.querySelector('.upload-area')
const fileLabel = document.querySelector('#file-label')

if (fileInput && uploadArea) {
  uploadArea.addEventListener('click', () => fileInput.click())

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0 && fileLabel) {
      fileLabel.textContent = fileInput.files[0].name
      uploadArea.style.borderColor = '#4F6EF7'
    }
  })

  // Drag and drop
  uploadArea.addEventListener('dragover', e => {
    e.preventDefault()
    uploadArea.style.borderColor = '#4F6EF7'
  })

  uploadArea.addEventListener('dragleave', () => {
    uploadArea.style.borderColor = ''
  })

  uploadArea.addEventListener('drop', e => {
    e.preventDefault()
    const files = e.dataTransfer.files
    if (files.length > 0) {
      fileInput.files = files
      if (fileLabel) fileLabel.textContent = files[0].name
    }
  })
}

// ─── Show loading on form submit ───
const meetingForm = document.querySelector('#meeting-form')
const loadingDiv = document.querySelector('#loading')
const formDiv = document.querySelector('#form-content')

if (meetingForm) {
  meetingForm.addEventListener('submit', () => {
    if (formDiv) formDiv.style.display = 'none'
    if (loadingDiv) loadingDiv.style.display = 'block'
  })
}

// ─── Delete confirmation ───
const deleteBtn = document.querySelector('#delete-btn')
if (deleteBtn) {
  deleteBtn.addEventListener('click', e => {
    if (!confirm('Are you sure you want to delete this meeting?')) {
      e.preventDefault()
    }
  })
}

// ─── Download notes ───
const downloadBtn = document.querySelector('#download-btn')
if (downloadBtn) {
  downloadBtn.addEventListener('click', () => {
    const title = document.querySelector('#meeting-title')?.textContent || 'Meeting'
    const summary = document.querySelector('#summary-text')?.textContent || ''
    const actions = [...document.querySelectorAll('.action-text')].map((el, i) => `${i + 1}. ${el.textContent}`).join('\n')
    const transcript = document.querySelector('.transcript-body')?.textContent || ''

    const content = `NoteTaker.AI — ${title}\n${'─'.repeat(40)}\n\nSUMMARY\n${summary}\n\nACTION ITEMS\n${actions}\n\nTRANSCRIPT\n${transcript}`

    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${title.toLowerCase().replace(/\s+/g, '-')}-notes.txt`
    a.click()
    URL.revokeObjectURL(url)
  })
}
