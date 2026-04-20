import { useState, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ticketsAPI } from '../services/api'
import * as XLSX from 'xlsx'
import { ArrowDownTrayIcon } from '@heroicons/react/24/outline'

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

// Dashboard filter groups → actual statuses
const FILTER_GROUPS = {
  all: [],
  open: ['new'],
  progress: ['assigned', 'in_progress', 'pending'],
  resolved: ['resolved'],
  closed: ['closed'],
  cancelled: ['cancelled'],
}

const PAGE_SIZE = 10

export default function Tickets() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [tickets, setTickets] = useState([])
  const [allTickets, setAllTickets] = useState([])
  const [loading, setLoading] = useState(true)
  const [currentPage, setCurrentPage] = useState(1)
  const [filters, setFilters] = useState({
    status: searchParams.get('filter') || '',
    priority: '',
  })

  useEffect(() => {
    fetchTickets()
  }, [])

  useEffect(() => {
    applyFilters()
  }, [filters, allTickets])

  // Sync URL param to filter state
  useEffect(() => {
    const urlFilter = searchParams.get('filter')
    if (urlFilter && urlFilter !== filters.status) {
      setFilters((prev) => ({ ...prev, status: urlFilter }))
    }
  }, [searchParams])

  const fetchTickets = async () => {
    try {
      const response = await ticketsAPI.getAll()
      setAllTickets(response.data)
    } catch (error) {
      console.error('Failed to fetch tickets:', error)
    } finally {
      setLoading(false)
    }
  }

  const applyFilters = () => {
    let filtered = [...allTickets]

    // Status filter (supports grouped filters from dashboard)
    if (filters.status && filters.status !== 'all') {
      const groupStatuses = FILTER_GROUPS[filters.status]
      if (groupStatuses) {
        filtered = filtered.filter((t) => groupStatuses.includes(t.status))
      } else {
        filtered = filtered.filter((t) => t.status === filters.status)
      }
    }

    // Priority filter
    if (filters.priority) {
      filtered = filtered.filter((t) => t.priority === filters.priority)
    }

    setTickets(filtered)
    setCurrentPage(1) // reset ke halaman pertama saat filter berubah
  }

  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }))
    // Update URL
    if (key === 'status') {
      if (value) {
        setSearchParams({ filter: value })
      } else {
        setSearchParams({})
      }
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

  const handleDownloadExcel = () => {
    if (tickets.length === 0) return

    const data = tickets.map((t, i) => ({
      No: i + 1,
      'Ticket ID': t.ticket_id,
      Title: t.title,
      Team: t.team_desc ? `${t.team_id} - ${t.team_desc}` : (t.department || '-'),
      Category: t.category || '-',
      Priority: t.priority || '-',
      Status: t.status,
      Requester: t.requester_fullname || t.requester_name || '-',
      PIC: t.pic_fullname || t.pic_name || '-',
      'Created At': t.created_at ? formatDate(t.created_at) : '-',
    }))

    const ws = XLSX.utils.json_to_sheet(data)

    // Auto-fit column widths
    const colWidths = Object.keys(data[0]).map((key) => ({
      wch: Math.max(key.length, ...data.map((row) => String(row[key] || '').length)) + 2,
    }))
    ws['!cols'] = colWidths

    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, 'Tickets')

    const dateStr = new Date().toISOString().slice(0, 10)
    XLSX.writeFile(wb, `Tickets_${dateStr}.xlsx`)
  }

  // Pagination computed values
  const totalPages = Math.ceil(tickets.length / PAGE_SIZE)
  const pagedTickets = tickets.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)

  const getPageNumbers = () => {
    const pages = []
    const delta = 2
    const left = Math.max(1, currentPage - delta)
    const right = Math.min(totalPages, currentPage + delta)
    for (let i = left; i <= right; i++) pages.push(i)
    if (left > 1) pages.unshift('...')
    if (left > 1) pages.unshift(1)
    if (right < totalPages) pages.push('...')
    if (right < totalPages) pages.push(totalPages)
    // deduplicate
    return [...new Set(pages)]
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Tickets</h1>
        <Link
          to="/tickets/new"
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          + New Ticket
        </Link>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 mb-6 flex gap-4">
        <select
          value={filters.status}
          onChange={(e) => handleFilterChange('status', e.target.value)}
          className="border rounded-lg px-3 py-2"
        >
          <option value="">All Status</option>
          <option value="new">New</option>
          <option value="in_progress">In Progress</option>
          <option value="pending">Pending</option>
          <option value="resolved">Resolved</option>
          <option value="closed">Closed</option>
          <option value="cancelled">Cancelled</option>
        </select>
        <select
          value={filters.priority}
          onChange={(e) => handleFilterChange('priority', e.target.value)}
          className="border rounded-lg px-3 py-2"
        >
          <option value="">All Priority</option>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="critical">Critical</option>
        </select>
        <button
          onClick={handleDownloadExcel}
          disabled={tickets.length === 0}
          className="ml-auto flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <ArrowDownTrayIcon className="h-5 w-5" />
          Download Excel
        </button>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg shadow overflow-x-auto">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        ) : tickets.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            No tickets found
          </div>
        ) : (
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase w-8">
                  #
                </th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase w-36">
                  Ticket ID
                </th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase w-40">
                  Title
                </th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase w-32">
                  Requester
                </th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase w-28">
                  Team
                </th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase w-20">
                  Priority
                </th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase w-24">
                  Status
                </th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase w-32">
                  PIC
                </th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase w-32">
                  Created
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {pagedTickets.map((ticket, index) => (
                <tr key={ticket.id} className="hover:bg-gray-50">
                  <td className="px-3 py-2 text-xs text-gray-500">
                    {(currentPage - 1) * PAGE_SIZE + index + 1}
                  </td>
                  <td className="px-3 py-2">
                    <Link
                      to={`/tickets/${ticket.id}`}
                      className="text-blue-600 hover:underline font-medium text-xs break-all"
                    >
                      {ticket.ticket_id}
                    </Link>
                  </td>
                  <td className="px-3 py-2">
                    <div className="w-40 break-words leading-snug">{ticket.title}</div>
                  </td>
                  <td className="px-3 py-2">
                    <div className="w-32 break-words">{ticket.requester_fullname || ticket.requester_name || '-'}</div>
                  </td>
                  <td className="px-3 py-2">
                    <div className="w-28 break-words">
                      {ticket.team_desc || ticket.department || '-'}
                    </div>
                  </td>
                  <td className="px-3 py-2 whitespace-nowrap">
                    <span
                      className={`px-2 py-1 rounded-full text-xs font-medium ${
                        priorityColors[ticket.priority] || 'bg-gray-100'
                      }`}
                    >
                      {ticket.priority}
                    </span>
                  </td>
                  <td className="px-3 py-2 whitespace-nowrap">
                    <span
                      className={`px-2 py-1 rounded-full text-xs font-medium ${
                        statusColors[ticket.status] || 'bg-gray-100'
                      }`}
                    >
                      {ticket.status}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <div className="w-32 break-words">{ticket.pic_fullname || ticket.pic_name || '-'}</div>
                  </td>
                  <td className="px-3 py-2 whitespace-nowrap text-xs text-gray-500">
                    {formatDate(ticket.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {!loading && tickets.length > 0 && (
        <div className="flex items-center justify-between mt-4 px-1">
          <p className="text-sm text-gray-500">
            Menampilkan {(currentPage - 1) * PAGE_SIZE + 1}–{Math.min(currentPage * PAGE_SIZE, tickets.length)} dari {tickets.length} tiket
          </p>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1 text-sm rounded border border-gray-300 hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              ‹ Prev
            </button>
            {getPageNumbers().map((page, idx) =>
              page === '...' ? (
                <span key={`ellipsis-${idx}`} className="px-2 text-gray-400">…</span>
              ) : (
                <button
                  key={page}
                  onClick={() => setCurrentPage(page)}
                  className={`px-3 py-1 text-sm rounded border ${
                    currentPage === page
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'border-gray-300 hover:bg-gray-100'
                  }`}
                >
                  {page}
                </button>
              )
            )}
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="px-3 py-1 text-sm rounded border border-gray-300 hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Next ›
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
