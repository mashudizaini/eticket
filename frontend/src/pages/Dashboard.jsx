import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { dashboardAPI } from '../services/api'
import {
  TicketIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline'
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts'

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6']

export default function Dashboard() {
  const navigate = useNavigate()
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchStats()
  }, [])

  const fetchStats = async () => {
    try {
      const response = await dashboardAPI.getStats()
      setStats(response.data)
    } catch (error) {
      console.error('Failed to fetch stats:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  const statCards = [
    { name: 'Total Tickets', value: stats?.total_tickets || 0, icon: TicketIcon, color: 'bg-blue-500', filter: 'all' },
    { name: 'Open', value: stats?.open_tickets || 0, icon: ClockIcon, color: 'bg-yellow-500', filter: 'open' },
    { name: 'In Progress', value: stats?.in_progress_tickets || 0, icon: ClockIcon, color: 'bg-purple-500', filter: 'progress' },
    { name: 'Resolved', value: stats?.resolved_tickets || 0, icon: CheckCircleIcon, color: 'bg-teal-500', filter: 'resolved' },
    { name: 'Closed', value: stats?.closed_tickets || 0, icon: CheckCircleIcon, color: 'bg-green-500', filter: 'closed' },
    { name: 'Cancelled', value: stats?.cancelled_tickets || 0, icon: XCircleIcon, color: 'bg-red-500', filter: 'cancelled' },
  ]

  const priorityData = stats?.tickets_by_priority
    ? Object.entries(stats.tickets_by_priority).map(([name, value]) => ({ name, value }))
    : []

  const deptData = stats?.tickets_by_department
    ? Object.entries(stats.tickets_by_department).map(([name, value]) => ({ name, value }))
    : []

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
        {statCards.map((card) => (
          <div
            key={card.name}
            onClick={() => navigate(`/tickets?filter=${card.filter}`)}
            className="bg-white rounded-lg shadow p-4 cursor-pointer hover:shadow-lg hover:scale-105 transition-all duration-200"
          >
            <div className="flex items-center">
              <div className={`p-2 rounded-full ${card.color}`}>
                <card.icon className="h-5 w-5 text-white" />
              </div>
              <div className="ml-3">
                <p className="text-xs text-gray-600">{card.name}</p>
                <p className="text-2xl font-bold">{card.value}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* This Month */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-sm font-semibold text-gray-600 mb-1">New This Month</h3>
          <p className="text-3xl font-bold text-blue-600">{stats?.new_this_month || 0}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-sm font-semibold text-gray-600 mb-1">Resolved This Month</h3>
          <p className="text-3xl font-bold text-teal-600">{stats?.resolved_this_month || 0}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-sm font-semibold text-gray-600 mb-1">Closed This Month</h3>
          <p className="text-3xl font-bold text-green-600">{stats?.closed_this_month || 0}</p>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* By Priority */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Tickets by Priority</h3>
          {priorityData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={priorityData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  dataKey="value"
                  label={({ name, value }) => `${name}: ${value}`}
                >
                  {priorityData.map((entry, index) => (
                    <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-gray-500 text-center py-8">No data available</p>
          )}
        </div>

        {/* By Team */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Tickets by Team</h3>
          {deptData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={deptData}>
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#3B82F6" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-gray-500 text-center py-8">No data available</p>
          )}
        </div>
      </div>
    </div>
  )
}
