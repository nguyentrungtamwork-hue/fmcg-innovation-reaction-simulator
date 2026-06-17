/** Guided-tour content registry (Phase 27). Copy is kept in sync with HELP_TEXT / Glossary. */

export interface TourStep {
  id: string;
  route?: string; // route to navigate to before showing the step (supports :projectId)
  target_selector?: string; // CSS selector to spotlight; falls back to a centered modal
  title: string;
  body: string;
  placement?: "top" | "bottom" | "left" | "right" | "center";
  action_hint?: string;
}

export interface Tour {
  id: string;
  name: string;
  steps: TourStep[];
}

export const TOUR_DISCLAIMER =
  "Demo tours explain simulated outputs. They do not represent real-world validated market forecasts.";

export const FIRST_TIME_TOUR: Tour = {
  id: "first_time",
  name: "First-Time Product Tour",
  steps: [
    {
      id: "welcome",
      route: "/",
      placement: "center",
      title: "Welcome to the FMCG Innovation Reaction Simulator",
      body: "This tool simulates how consumers and market actors might react to a new product concept across a launch funnel. Everything is exploratory decision support · not a market forecast.",
    },
    {
      id: "samples",
      route: "/samples",
      target_selector: "[data-tour='samples-grid']",
      placement: "top",
      title: "Start from a sample concept",
      body: "The Sample Library has ready-made (fictional) FMCG concepts. Load one as a new project to explore the full workflow in seconds.",
      action_hint: "Use 'Load as new project' or 'Load and run pipeline'.",
    },
    {
      id: "home",
      route: "/",
      target_selector: "[data-tour='nav-projects']",
      placement: "bottom",
      title: "Your projects live here",
      body: "Each project runs the pipeline: brief → ontology → agents → simulation → report → Q&A → scenarios. Project Home shows status and the recommended next step.",
    },
    {
      id: "studio",
      route: "/",
      target_selector: "[data-tour='nav-samples']",
      placement: "bottom",
      title: "Agent Studio",
      body: "Once a project has agents, Agent Studio lets you watch reactions form (Live Mode), replay saved runs, and inspect individual agents.",
    },
    {
      id: "report",
      route: "/",
      placement: "center",
      title: "Report & Briefing",
      body: "The Report is a 16-section strategic read grounded in simulated evidence. The Briefing turns it into an executive-ready narrative you can tailor by audience.",
    },
    {
      id: "scenarios",
      route: "/",
      placement: "center",
      title: "Scenario Lab",
      body: "Stress-test what-if levers (price, sampling, claim credibility, channel focus…) without touching the baseline. Compare baseline vs scenario deltas.",
    },
    {
      id: "export",
      route: "/data-tools",
      target_selector: "[data-tour='data-tools-root']",
      placement: "top",
      title: "Save or share your work",
      body: "Export a project as a single no-secret JSON bundle, import one back, or back up / reset the local database. That's the whole tour · enjoy exploring!",
    },
  ],
};

export const STUDIO_TOUR: Tour = {
  id: "studio",
  name: "Agent Studio Tour",
  steps: [
    {
      id: "studio-intro",
      target_selector: "[data-tour='studio-root']",
      placement: "center",
      title: "Agent Studio",
      body: "This is where the simulation comes alive. You can run it live, replay a saved run, and explore how each agent reacted round by round.",
    },
    {
      id: "studio-live",
      target_selector: "[data-tour='studio-live']",
      placement: "bottom",
      title: "Live Mode vs Replay Mode",
      body: "Live Mode streams a fresh run as the backend generates and persists it. Replay Mode animates already-saved events client-side · no recomputation.",
    },
    {
      id: "studio-canvas",
      target_selector: "[data-tour='studio-canvas']",
      placement: "top",
      title: "Agent network & round timeline",
      body: "The canvas shows agents reacting; the round timeline scrubs through the 6 launch stages. Click an agent to open its drawer with traits, memory, and action history.",
    },
    {
      id: "studio-stream",
      target_selector: "[data-tour='studio-stream']",
      placement: "left",
      title: "Live event stream & filters",
      body: "Each event is one agent's action with scores (sentiment, trial, repeat). Filters narrow by round, segment, or action type.",
    },
    {
      id: "studio-disclaimer",
      placement: "center",
      title: "About the network edges",
      body: "Edges between agents are heuristic visual groupings (e.g. shared segment), not a measured social graph. Treat the whole view as exploratory decision support · simulated reactions, not a real-world forecast.",
    },
  ],
};

export const TOURS: Record<string, Tour> = {
  [FIRST_TIME_TOUR.id]: FIRST_TIME_TOUR,
  [STUDIO_TOUR.id]: STUDIO_TOUR,
};

export function getTour(id: string): Tour | undefined {
  return TOURS[id];
}
