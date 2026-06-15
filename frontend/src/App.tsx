import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import LoadingState from "./components/LoadingState";
import ProjectListPage from "./pages/ProjectListPage";
import ProjectHomePage from "./pages/ProjectHomePage";
import ProjectWorkflowPage from "./pages/ProjectWorkflowPage";
import QAConsolePage from "./pages/QAConsolePage";
import ScenarioLabPage from "./pages/ScenarioLabPage";
import SensitivityPage from "./pages/SensitivityPage";
import SnapshotDiffPage from "./pages/SnapshotDiffPage";
import DecisionHistoryPage from "./pages/DecisionHistoryPage";
import DataToolsPage from "./pages/DataToolsPage";
import SampleLibraryPage from "./pages/SampleLibraryPage";
import SampleDetailPage from "./pages/SampleDetailPage";
import TourProvider from "./tours/TourProvider";

// Code-split the heaviest routes to cut initial JS.
const ReportPage = lazy(() => import("./pages/ReportPage"));
const EventExplorerPage = lazy(() => import("./pages/EventExplorerPage"));
const PortfolioPage = lazy(() => import("./pages/PortfolioPage"));
const ComparePage = lazy(() => import("./pages/ComparePage"));
const BriefingPage = lazy(() => import("./pages/BriefingPage"));
const AgentStudioPage = lazy(() => import("./pages/AgentStudioPage"));
const DecisionPackPage = lazy(() => import("./pages/DecisionPackPage"));
const PortfolioDecisionBoardPage = lazy(() => import("./pages/PortfolioDecisionBoardPage"));
const PipelineBoardPage = lazy(() => import("./pages/PipelineBoardPage"));
const PortfolioActivityPage = lazy(() => import("./pages/PortfolioActivityPage"));

export default function App() {
  return (
    <TourProvider>
    <Suspense fallback={<div className="mx-auto max-w-7xl px-4 py-6"><LoadingState label="Loading…" /></div>}>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<ProjectListPage />} />
          <Route path="portfolio" element={<PortfolioPage />} />
          <Route path="compare" element={<ComparePage />} />
          <Route path="portfolio/decision-board" element={<PortfolioDecisionBoardPage />} />
          <Route path="portfolio/pipeline" element={<PipelineBoardPage />} />
          <Route path="portfolio/activity" element={<PortfolioActivityPage />} />
          <Route path="data-tools" element={<DataToolsPage />} />
          <Route path="samples" element={<SampleLibraryPage />} />
          <Route path="samples/:sampleId" element={<SampleDetailPage />} />
          <Route path="projects/:projectId/home" element={<ProjectHomePage />} />
          <Route path="projects/:projectId/workflow" element={<ProjectWorkflowPage />} />
          <Route path="projects/:projectId/events" element={<EventExplorerPage />} />
          <Route path="projects/:projectId/report" element={<ReportPage />} />
          <Route path="projects/:projectId/qa" element={<QAConsolePage />} />
          <Route path="projects/:projectId/scenarios" element={<ScenarioLabPage />} />
          <Route path="projects/:projectId/sensitivity" element={<SensitivityPage />} />
          <Route path="projects/:projectId/snapshots/diff" element={<SnapshotDiffPage />} />
          <Route path="projects/:projectId/decisions" element={<DecisionHistoryPage />} />
          <Route path="projects/:projectId/briefing" element={<BriefingPage />} />
          <Route path="projects/:projectId/studio" element={<AgentStudioPage />} />
          <Route path="projects/:projectId/decision-pack" element={<DecisionPackPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </Suspense>
    </TourProvider>
  );
}
