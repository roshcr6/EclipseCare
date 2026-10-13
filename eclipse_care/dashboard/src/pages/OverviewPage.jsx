import SmartAlertFeed from '../components/SmartAlertFeed'
import ResidentList from '../components/ResidentList'
import UnitSummaryWidget from '../components/UnitSummaryWidget'
import LiveLocationMap from '../components/LiveLocationMap'

export default function OverviewPage() {
  return (
    <div className="bento-grid">
      {/* Top Row */}
      <UnitSummaryWidget />
      <SmartAlertFeed />
      
      {/* Bottom Row */}
      <ResidentList />
      <LiveLocationMap />
    </div>
  )
}
