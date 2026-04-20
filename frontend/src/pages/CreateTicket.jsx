import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ticketsAPI } from '../services/api'
import toast from 'react-hot-toast'
import { XMarkIcon } from '@heroicons/react/24/outline'

const categories = ['Hardware', 'Software', 'Network', 'Access', 'Other']
const priorities = ['low', 'medium', 'high', 'critical']

export default function CreateTicket() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [teams, setTeams] = useState([])
  const [myTeamId, setMyTeamId] = useState(null) // null = belum selesai fetch
  const [form, setForm] = useState({
    title: '',
    description: '',
    department: '',
    category: '',
    priority: 'medium',
  })
  const [files, setFiles] = useState([])

  useEffect(() => {
    // Fetch paralel: teams list & my team dari Oracle
    Promise.all([
      ticketsAPI.getTeams().catch(() => ({ data: [] })),
      ticketsAPI.getMyTeam().catch(() => ({ data: { team_id: '', team_desc: '' } })),
    ]).then(([teamsRes, myTeamRes]) => {
      const teamList = teamsRes.data || []
      const tid = myTeamRes.data?.team_id || ''
      setTeams(teamList)
      setMyTeamId(tid)
      // Set department hanya setelah kedua data tersedia
      if (tid) {
        setForm((prev) => ({ ...prev, department: tid }))
      }
    })
  }, [])

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value })
  }

  const handleFileChange = (e) => {
    const newFiles = Array.from(e.target.files)
    if (files.length + newFiles.length > 5) {
      toast.error('Maximum 5 files allowed')
      return
    }
    setFiles([...files, ...newFiles])
  }

  const removeFile = (index) => {
    setFiles(files.filter((_, i) => i !== index))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)

    try {
      await ticketsAPI.create({ ...form, files })
      toast.success('Ticket created successfully!')
      navigate('/tickets')
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create ticket')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Create New Ticket</h1>

      <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-6 space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Title <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            name="title"
            value={form.title}
            onChange={handleChange}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Brief description of the issue"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Description <span className="text-red-500">*</span>
          </label>
          <textarea
            name="description"
            value={form.description}
            onChange={handleChange}
            rows={4}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Detailed description of the issue..."
            required
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Team
            </label>
            <select
              key={`team-${form.department}`}
              name="department"
              value={form.department}
              onChange={handleChange}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
              required
              disabled={myTeamId !== null && !!myTeamId}
            >
              <option value="">Select Team</option>
              {teams.map((team) => (
                <option key={team.team_id} value={team.team_id}>
                  {team.team_desc}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Category <span className="text-red-500">*</span>
            </label>
            <select
              name="category"
              value={form.category}
              onChange={handleChange}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              required
            >
              <option value="">Select Category</option>
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Priority
          </label>
          <div className="flex gap-4">
            {priorities.map((p) => (
              <label key={p} className="flex items-center">
                <input
                  type="radio"
                  name="priority"
                  value={p}
                  checked={form.priority === p}
                  onChange={handleChange}
                  className="mr-2"
                />
                <span className="text-sm capitalize">{p}</span>
              </label>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Attachments (max 5 files, 2MB each)
          </label>
          <input
            type="file"
            multiple
            onChange={handleFileChange}
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            accept=".jpg,.jpeg,.png,.pdf,.doc,.docx,.xls,.xlsx"
          />
          {files.length > 0 && (
            <div className="mt-2 space-y-2">
              {files.map((file, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between bg-gray-50 px-3 py-2 rounded"
                >
                  <span className="text-sm truncate">{file.name}</span>
                  <button
                    type="button"
                    onClick={() => removeFile(index)}
                    className="text-red-500 hover:text-red-700"
                  >
                    <XMarkIcon className="h-5 w-5" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="flex gap-4">
          <button
            type="button"
            onClick={() => navigate('/tickets')}
            className="flex-1 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="flex-1 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Creating...' : 'Create Ticket'}
          </button>
        </div>
      </form>
    </div>
  )
}
