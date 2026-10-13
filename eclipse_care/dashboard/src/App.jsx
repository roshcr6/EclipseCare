import { Routes, Route } from 'react-router-dom'
import DashboardLayout from './components/DashboardLayout'
import OverviewPage from './pages/OverviewPage'
import HandoffPage from './pages/HandoffPage'
import EmarPage from './pages/EmarPage'

function App() {
  return (
    <DashboardLayout>
      <Routes>
        <Route path="/" element={<OverviewPage />} />
        <Route path="/handoff" element={<HandoffPage />} />
        <Route path="/emar" element={<EmarPage />} />
      </Routes>
    </DashboardLayout>
  )
}

export default App
