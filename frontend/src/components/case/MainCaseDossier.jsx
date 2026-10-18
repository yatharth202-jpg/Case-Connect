import React, { useState } from 'react';
import { useCaseFlow } from '../../context/CaseFlowContext';
import SuspectHero from './SuspectHero';
import SuspectRow from './SuspectRow';
import MoneyCallArcs from './MoneyCallArcs';
import NetworkSection from './NetworkSection';
import ChartsGrid from './ChartsGrid';
import EvidenceTable from './EvidenceTable';
import AboutFooter from './AboutFooter';

export const MainCaseDossier = () => {
  const { activeCaseData, activeCaseId } = useCaseFlow();
  const [selectedEntity, setSelectedEntity] = useState(null);

  // Derive primary lead dynamically from active case API data
  const dynamicPrimaryLead = activeCaseData?.top_lead || activeCaseData?.prime_suspect || (
    activeCaseData?.leads && activeCaseData.leads.length > 0 ? activeCaseData.leads[0] : null
  );

  const primaryLead = selectedEntity || dynamicPrimaryLead || {
    name: activeCaseData?.case?.title || activeCaseData?.title || 'Primary Focal Node',
    role: 'Attributed Key Entity',
    city: 'Jurisdiction Lead',
    score: 82,
    phones_count: activeCaseData?.overview?.total_calls ? `${activeCaseData.overview.total_calls} Calls` : 'Correlated',
    accounts_count: activeCaseData?.overview?.total_txns ? `${activeCaseData.overview.total_txns} Txns` : 'Staged',
    volume_routed: activeCaseData?.overview?.total_money_volume_rs
      ? `₹ ${(activeCaseData.overview.total_money_volume_rs / 100000).toFixed(2)} Lakh`
      : 'Calculated',
    factors: [
      { name: 'Telecommunication Graph Density', points: 32, desc: 'Central communication hub identified across ingested CDR call records' },
      { name: 'Transaction Layering Velocity', points: 30, desc: 'Rapid movement of funds across staged banking accounts' },
      { name: 'Cross-Corroboration Match', points: 20, desc: 'Co-occurrence in multi-jurisdiction police records' }
    ]
  };

  // Secondary correlated leads
  const rawSecondary = activeCaseData?.other_leads || (
    activeCaseData?.leads && activeCaseData.leads.length > 1 ? activeCaseData.leads.slice(1, 5) : []
  );

  const secondaryLeads = Array.isArray(rawSecondary) ? rawSecondary : [];

  return (
    <div className="w-full flex flex-col space-y-4">
      {/* S1: Attributed Lead Hero Card */}
      <SuspectHero
        activeEntity={primaryLead}
      />

      {/* S2: Correlated Leads Matrix (1-Click Swap) */}
      {secondaryLeads.length > 0 && (
        <SuspectRow
          leads={secondaryLeads}
          selectedLeadId={primaryLead.canonical_id || primaryLead.id}
          onSelectLead={(entity) => setSelectedEntity(entity)}
        />
      )}

      {/* S3: Ballistic Money and Call Arcs Centerpiece */}
      <MoneyCallArcs
        flowData={{
          total_volume: activeCaseData?.overview?.total_money_volume_rs || 18450000,
          total_calls: activeCaseData?.overview?.total_calls || 1842,
          mule_accounts_count: activeCaseData?.overview?.total_accounts || 7
        }}
      />

      {/* S4: Cytoscape Topological Linkage Network Graph */}
      <NetworkSection
        caseId={activeCaseId}
        initialGraphData={activeCaseData?.cytoscape || activeCaseData?.graph}
        selectedLeadId={primaryLead.canonical_id || primaryLead.id}
        onSelectEntity={(entity) => setSelectedEntity(entity)}
      />

      {/* S5: Quantitative Forensics 6-Chart Analytical Grid */}
      <ChartsGrid
        chartsData={activeCaseData?.charts || activeCaseData?.analytics}
      />

      {/* S6: Verified Evidence Ledger with Preview Modal */}
      <EvidenceTable
        evidenceRecords={activeCaseData?.evidence_records || []}
      />

      {/* S7: Executive UNITx Brand Footer */}
      <AboutFooter />
    </div>
  );
};

export default MainCaseDossier;
