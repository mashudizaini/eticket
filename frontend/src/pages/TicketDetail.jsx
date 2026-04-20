import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ticketsAPI, dashboardAPI } from '../services/api'
import { useAuth } from '../context/AuthContext'
import toast from 'react-hot-toast'
import {
  ClockIcon,
  UserIcon,
  CheckCircleIcon,
  XCircleIcon,
  PaperClipIcon,
  ChevronDownIcon,
} from '@heroicons/react/24/outline'

const statusColors = {
  new: 'bg-yellow-100 text-yellow-800',
  assigned: 'bg-blue-100 text-blue-800',
  in_progress: 'bg-purple-100 text-purple-800',
  pending: 'bg-orange-100 text-orange-800',
  resolved: 'bg-green-100 text-green-800',
  closed: 'bg-green-100 text-green-800',
  cancelled: 'bg-red-100 text-red-800',
}

const priorityColors = {
  low: 'bg-gray-100 text-gray-800',
  medium: 'bg-blue-100 text-blue-800',
  high: 'bg-orange-100 text-orange-800',
  critical: 'bg-red-100 text-red-800',
}

const actionIcons = {
  CREATED: ClockIcon,
  ASSIGNED: UserIcon,
  UPDATED: ClockIcon,
  CLOSED: CheckCircleIcon,
  CANCELLED: XCircleIcon,
}

export default function TicketDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [ticket, setTicket] = useState(null)
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [showAssignModal, setShowAssignModal] = useState(false)
  const [showFinishModal, setShowFinishModal] = useState(false)
  const [showPostponeModal, setShowPostponeModal] = useState(false)
  const [showCancelModal, setShowCancelModal] = useState(false)
  const [showCloseModal, setShowCloseModal] = useState(false)
  const [showActionMenu, setShowActionMenu] = useState(false)

  // Form states
  const [assignForm, setAssignForm] = useState({ pic_id: '', pic_name: '', description: '' })
  const [finishForm, setFinishForm] = useState({ resolution_status: 'accepted', resolution: '' })
  const [postponeForm, setPostponeForm] = useState({ description: '' })
  const [cancelForm, setCancelForm] = useState({ cancel_reason: '' })
  const [closeNote, setCloseNote] = useState('')

  useEffect(() => {
    fetchTicket()
    fetchUsers()
  }, [id])

  const fetchTicket = async () => {
    try {
      console.log('[DEBUG] Fetching ticket with id:', id)
      const response = await ticketsAPI.getOne(id)
      console.log('[DEBUG] Response:', response)
      console.log('[DEBUG] Response data:', response.data)
      setTicket(response.data)
    } catch (error) {
      console.error('[DEBUG] Error fetching ticket:', error)
      toast.error('Failed to fetch ticket')
      navigate('/tickets')
    } finally {
      setLoading(false)
    }
  }

  const fetchUsers = async () => {
    try {
      const response = await dashboardAPI.getUsers()
      setUsers(response.data)
    } catch (error) {
      console.error('Failed to fetch users:', error)
    }
  }

  const handleAssign = async () => {
    try {
      await ticketsAPI.assign(id, {
        pic_id: parseInt(assignForm.pic_id),
        pic_name: assignForm.pic_name,
        description: assignForm.description,
      })
      toast.success('PIC assigned successfully')
      setShowAssignModal(false)
      setAssignForm({ pic_id: '', pic_name: '', description: '' })
      fetchTicket()
    } catch (error) {
      toast.error('Failed to assign PIC')
    }
  }

  const handleFinish = async () => {
    try {
      await ticketsAPI.finish(id, finishForm)
      toast.success('Ticket closed successfully')
      setShowFinishModal(false)
      fetchTicket()
    } catch (error) {
      toast.error('Failed to close ticket')
    }
  }

  const handleCancel = async () => {
    try {
      await ticketsAPI.cancel(id, cancelForm)
      toast.success('Ticket cancelled')
      setShowCancelModal(false)
      fetchTicket()
    } catch (error) {
      toast.error('Failed to cancel ticket')
    }
  }

  const handlePostpone = async () => {
    try {
      await ticketsAPI.postpone(id, postponeForm)
      toast.success('Ticket postponed')
      setShowPostponeModal(false)
      setPostponeForm({ description: '' })
      fetchTicket()
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to postpone ticket')
    }
  }

  const handleClose = async () => {
    try {
      await ticketsAPI.close(id)
      toast.success('Ticket closed successfully')
      setShowCloseModal(false)
      fetchTicket()
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to close ticket')
    }
  }

  const formatDate = (date) => {
    return new Date(date).toLocaleDateString('id-ID', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (!ticket) return null

  const canAssign = ['IT', 'PLANT', 'ADM'].includes(user?.team) && ticket.status === 'new'
  const canAction = ['IT', 'PLANT'].includes(user?.team) && ['in_progress', 'pending'].includes(ticket.status)
  const canClose = ticket.requester_name === user?.employee_number && ticket.status === 'resolved'

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex justify-between items-start mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{ticket.ticket_id}</h1>
          <p className="text-gray-600 mt-1">{ticket.title}</p>
        </div>
        <div className="flex gap-2">
          {canAssign && (
            <button
              onClick={() => setShowAssignModal(true)}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
            >
              Assign PIC
            </button>
          )}
          {canAction && (
            <div className="relative">
              <button
                onClick={() => setShowActionMenu(!showActionMenu)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
              >
                Action
                <ChevronDownIcon className="h-4 w-4" />
              </button>
              {showActionMenu && (
                <div className="absolute right-0 mt-1 w-40 bg-white border rounded-lg shadow-lg z-10">
                  <button
                    onClick={() => { setShowActionMenu(false); setShowFinishModal(true) }}
                    className="w-full text-left px-4 py-2 hover:bg-gray-50 text-sm rounded-t-lg"
                  >
                    Resolve
                  </button>
                  <button
                    onClick={() => { setShowActionMenu(false); setShowPostponeModal(true) }}
                    className="w-full text-left px-4 py-2 hover:bg-gray-50 text-sm"
                  >
                    Postpone
                  </button>
                  <button
                    onClick={() => { setShowActionMenu(false); setShowCancelModal(true) }}
                    className="w-full text-left px-4 py-2 hover:bg-gray-50 text-sm text-red-600 rounded-b-lg"
                  >
                    Cancel
                  </button>
                </div>
              )}
            </div>
          )}
          {canClose && (
            <button
              onClick={() => setShowCloseModal(true)}
              className="px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700"
            >
              Close Ticket
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Main Info */}
        <div className="col-span-2 space-y-6">
          {/* Details Card */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">Details</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-500">Status</p>
                <span className={`inline-block mt-1 px-2 py-1 rounded-full text-xs font-medium ${statusColors[ticket.status]}`}>
                  {ticket.status}
                </span>
              </div>
              <div>
                <p className="text-sm text-gray-500">Priority</p>
                <span className={`inline-block mt-1 px-2 py-1 rounded-full text-xs font-medium ${priorityColors[ticket.priority]}`}>
                  {ticket.priority}
                </span>
              </div>
              <div>
                <p className="text-sm text-gray-500">Team</p>
                <p className="mt-1 font-medium">
                  {ticket.team_desc ? `${ticket.team_id} - ${ticket.team_desc}` : (ticket.department || '-')}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Category</p>
                <p className="mt-1 font-medium">{ticket.category || '-'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Requester</p>
                <p className="mt-1 font-medium">{ticket.requester_fullname || ticket.requester_name}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">PIC</p>
                <p className="mt-1 font-medium">{ticket.pic_fullname || ticket.pic_name || '-'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Created</p>
                <p className="mt-1 font-medium">{formatDate(ticket.created_at)}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Closed</p>
                <p className="mt-1 font-medium">{ticket.closed_at ? formatDate(ticket.closed_at) : '-'}</p>
              </div>
            </div>

            {ticket.description && (
              <div className="mt-6">
                <p className="text-sm text-gray-500 mb-2">Description</p>
                <p className="text-gray-700 whitespace-pre-wrap">{ticket.description}</p>
              </div>
            )}

            {ticket.resolution && (
              <div className="mt-6 p-4 bg-green-50 rounded-lg">
                <p className="text-sm text-gray-500 mb-2">Resolution ({ticket.resolution_status})</p>
                <p className="text-gray-700">{ticket.resolution}</p>
              </div>
            )}

            {ticket.cancel_reason && (
              <div className="mt-6 p-4 bg-red-50 rounded-lg">
                <p className="text-sm text-gray-500 mb-2">Cancel Reason</p>
                <p className="text-gray-700">{ticket.cancel_reason}</p>
              </div>
            )}
          </div>

          {/* Attachments */}
          {ticket.attachments?.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Attachments</h2>
              <div className="space-y-2">
                {ticket.attachments.map((att) => (
                  <a
                    key={att.id}
                    href={`/${att.file_path}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 p-2 hover:bg-gray-50 rounded"
                  >
                    <PaperClipIcon className="h-5 w-5 text-gray-400" />
                    <span className="text-blue-600 hover:underline">{att.file_name}</span>
                    <span className="text-sm text-gray-500">
                      ({(att.file_size / 1024).toFixed(1)} KB)
                    </span>
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Timeline */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Timeline</h2>
          <div className="space-y-4">
            {ticket.history?.map((item, index) => {
              const Icon = actionIcons[item.action] || ClockIcon
              return (
                <div key={item.id} className="flex gap-3">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                      <Icon className="h-4 w-4 text-blue-600" />
                    </div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">{item.action}</p>
                    {item.description && (
                      <p className="text-sm text-gray-600 mt-1">{item.description}</p>
                    )}
                    <p className="text-xs text-gray-400 mt-1">
                      {item.actor_name} - {formatDate(item.created_at)}
                    </p>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Assign Modal */}
      {showAssignModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold mb-4">Assign PIC</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Select PIC
                </label>
                <select
                  value={assignForm.pic_id}
                  onChange={(e) => {
                    const selectedUser = users.find(u => u.person_id === parseInt(e.target.value))
                    setAssignForm({
                      ...assignForm,
                      pic_id: e.target.value,
                      pic_name: selectedUser?.employee_number || ''
                    })
                  }}
                  className="w-full px-4 py-2 border rounded-lg"
                >
                  <option value="">Select User</option>
                  {users.map((u) => (
                    <option key={u.person_id} value={u.person_id}>
                      {u.full_name} ({u.department})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Note
                </label>
                <textarea
                  value={assignForm.description}
                  onChange={(e) => setAssignForm({ ...assignForm, description: e.target.value })}
                  rows={3}
                  className="w-full px-4 py-2 border rounded-lg"
                />
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowAssignModal(false)}
                className="flex-1 py-2 border rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleAssign}
                disabled={!assignForm.pic_id}
                className="flex-1 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
              >
                Assign
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Finish Modal */}
      {showFinishModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold mb-4">Resolve Ticket</h3>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Resolution Note
              </label>
              <textarea
                value={finishForm.resolution}
                onChange={(e) => setFinishForm({ ...finishForm, resolution: e.target.value })}
                rows={3}
                className="w-full px-4 py-2 border rounded-lg"
              />
            </div>
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowFinishModal(false)}
                className="flex-1 py-2 border rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleFinish}
                className="flex-1 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
              >
                Resolve Ticket
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Postpone Modal */}
      {showPostponeModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold mb-4">Postpone Ticket</h3>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                value={postponeForm.description}
                onChange={(e) => setPostponeForm({ description: e.target.value })}
                rows={3}
                placeholder="Reason for postponing..."
                className="w-full px-4 py-2 border rounded-lg"
              />
            </div>
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => { setShowPostponeModal(false); setPostponeForm({ description: '' }) }}
                className="flex-1 py-2 border rounded-lg hover:bg-gray-50"
              >
                Back
              </button>
              <button
                onClick={handlePostpone}
                className="flex-1 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600"
              >
                Postpone
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Cancel Modal */}
      {showCancelModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold mb-4">Cancel Ticket</h3>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Cancel Reason
              </label>
              <textarea
                value={cancelForm.cancel_reason}
                onChange={(e) => setCancelForm({ cancel_reason: e.target.value })}
                rows={3}
                className="w-full px-4 py-2 border rounded-lg"
                required
              />
            </div>
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowCancelModal(false)}
                className="flex-1 py-2 border rounded-lg hover:bg-gray-50"
              >
                Back
              </button>
              <button
                onClick={handleCancel}
                disabled={!cancelForm.cancel_reason}
                className="flex-1 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
              >
                Cancel Ticket
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Close Modal */}
      {showCloseModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold mb-4">Close Ticket</h3>
            <p className="text-gray-600 mb-4">
              Ticket ini telah diselesaikan oleh tim IT/PLANT. Apakah Anda konfirmasi untuk menutup ticket ini?
            </p>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Catatan (opsional)
              </label>
              <textarea
                value={closeNote}
                onChange={(e) => setCloseNote(e.target.value)}
                rows={3}
                placeholder="Tambahkan catatan penutupan..."
                className="w-full px-4 py-2 border rounded-lg"
              />
            </div>
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowCloseModal(false)}
                className="flex-1 py-2 border rounded-lg hover:bg-gray-50"
              >
                Batal
              </button>
              <button
                onClick={handleClose}
                className="flex-1 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700"
              >
                Konfirmasi Tutup
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
