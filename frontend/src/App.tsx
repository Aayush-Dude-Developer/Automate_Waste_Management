import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import DashboardView from './views/DashboardView';
import InventoryView from './views/InventoryView';
import PurchaseRecommendationsView from './views/PurchaseRecommendationsView';
import PurchaseInvoicesView from './views/PurchaseInvoicesView';
import BuffetPlanningView from './views/BuffetPlanningView';
import SurplusWasteView from './views/SurplusWasteView';
import DonationCentresView from './views/DonationCentresView';
import DocumentsView from './views/DocumentsView';
import ImpactReportsView from './views/ImpactReportsView';
import SettingsView from './views/SettingsView';
import RecipesView from './views/RecipesView';
import MonthlyStockView from './views/MonthlyStockView';

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<DashboardView />} />
          <Route path="/inventory" element={<InventoryView />} />
          <Route path="/sales-purchases" element={<PurchaseRecommendationsView />} />
          <Route path="/purchases" element={<PurchaseInvoicesView />} />
          <Route path="/recipes" element={<RecipesView />} />
          <Route path="/stock-balances" element={<MonthlyStockView />} />
          <Route path="/buffet-planning" element={<BuffetPlanningView />} />
          <Route path="/surplus-waste" element={<SurplusWasteView />} />
          <Route path="/donations" element={<DonationCentresView />} />
          <Route path="/documents" element={<DocumentsView />} />
          <Route path="/impact" element={<ImpactReportsView />} />
          <Route path="/settings" element={<SettingsView />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
