import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import Layout from './components/Layout'
import Home from './pages/Home'
import PatientJourney from './pages/PatientJourney'
import NoteExplorer from './pages/NoteExplorer'
import ConsistencyInvestigation from './pages/ConsistencyInvestigation'
import TextIntelligence from './pages/TextIntelligence'
import Evaluation from './pages/Evaluation'
import ImportNotes from './pages/ImportNotes'

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <AnimatePresence mode="wait">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/import" element={<ImportNotes />} />
            <Route path="/journey" element={<PatientJourney />} />
            <Route path="/notes" element={<NoteExplorer />} />
            <Route path="/consistency" element={<ConsistencyInvestigation />} />
            <Route path="/intelligence" element={<TextIntelligence />} />
            <Route path="/evaluation" element={<Evaluation />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AnimatePresence>
      </Layout>
    </BrowserRouter>
  )
}
