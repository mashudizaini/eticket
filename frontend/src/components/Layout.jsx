import { Outlet, Link, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import {
  HomeIcon,
  TicketIcon,
  PlusCircleIcon,
  ArrowRightOnRectangleIcon,
} from '@heroicons/react/24/outline'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: HomeIcon },
  { name: 'Tickets', href: '/tickets', icon: TicketIcon },
  { name: 'New Ticket', href: '/tickets/new', icon: PlusCircleIcon },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const location = useLocation()

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <div className="w-64 bg-gray-900 text-white">
        <div className="p-4 flex items-center gap-3">
          <img src="/logo-sidebar.png" alt="CKD Otto" className="h-10 w-auto" />
          <h1 className="text-xl font-bold">E-Ticket</h1>
        </div>
        <nav className="mt-4">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`flex items-center px-4 py-3 text-sm ${
                  isActive
                    ? 'bg-gray-800 border-l-4 border-blue-500'
                    : 'hover:bg-gray-800'
                }`}
              >
                <item.icon className="h-5 w-5 mr-3" />
                {item.name}
              </Link>
            )
          })}
        </nav>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col">
        {/* Top bar */}
        <header className="bg-white shadow h-16 relative">
          {/* Full-width logo background */}
          <img
            src="/logo-header-full.png"
            alt="CKD Otto"
            className="absolute inset-0 w-full h-full object-contain object-left"
          />
          {/* User info overlay on the right */}
          <div className="absolute right-0 top-0 h-full flex items-center gap-4 px-6 bg-white/90">
            <span className="text-sm text-gray-600">
              {user?.full_name} ({user?.role})
            </span>
            <button
              onClick={logout}
              className="flex items-center text-sm text-gray-600 hover:text-gray-900"
            >
              <ArrowRightOnRectangleIcon className="h-5 w-5 mr-1" />
              Logout
            </button>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 p-6 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
