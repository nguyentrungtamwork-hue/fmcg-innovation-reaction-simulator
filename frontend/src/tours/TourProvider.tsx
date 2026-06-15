import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getTour, type Tour, type TourStep } from "./tours";
import TourOverlay from "./TourOverlay";

const SEEN_KEY = "guided_tour_seen";
const STEP_KEY = "guided_tour_current_step";

interface TourState {
  tour: Tour | null;
  index: number;
}

interface TourContextValue {
  active: boolean;
  tour: Tour | null;
  index: number;
  step: TourStep | null;
  startTour: (tourId: string, projectId?: string) => void;
  next: () => void;
  prev: () => void;
  skip: () => void;
  finish: () => void;
  resetTourState: () => void;
}

const TourContext = createContext<TourContextValue | null>(null);

const NOOP_TOUR: TourContextValue = {
  active: false,
  tour: null,
  index: 0,
  step: null,
  startTour: () => {},
  next: () => {},
  prev: () => {},
  skip: () => {},
  finish: () => {},
  resetTourState: () => {},
};

export function useTour(): TourContextValue {
  // Fall back to a no-op so components (e.g. DemoControlPanel) can render outside
  // a TourProvider (e.g. in isolated tests) without crashing.
  return useContext(TourContext) ?? NOOP_TOUR;
}

export function isTourSeen(): boolean {
  try {
    return localStorage.getItem(SEEN_KEY) === "true";
  } catch {
    return false;
  }
}

function resolveRoute(route: string | undefined, projectId: string | undefined): string | undefined {
  if (!route) return undefined;
  return projectId ? route.replace(":projectId", projectId) : route;
}

export default function TourProvider({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const [{ tour, index }, setState] = useState<TourState>({ tour: null, index: 0 });
  const [projectId, setProjectId] = useState<string | undefined>(undefined);

  const goTo = useCallback(
    (t: Tour, i: number, pid: string | undefined) => {
      const stepRoute = resolveRoute(t.steps[i]?.route, pid);
      if (stepRoute) navigate(stepRoute);
      try {
        localStorage.setItem(STEP_KEY, JSON.stringify({ tourId: t.id, index: i, projectId: pid }));
      } catch {
        /* ignore */
      }
    },
    [navigate]
  );

  const startTour = useCallback(
    (tourId: string, pid?: string) => {
      const t = getTour(tourId);
      if (!t) return;
      setProjectId(pid);
      setState({ tour: t, index: 0 });
      goTo(t, 0, pid);
    },
    [goTo]
  );

  const endTour = useCallback(() => {
    setState({ tour: null, index: 0 });
    try {
      localStorage.setItem(SEEN_KEY, "true");
      localStorage.removeItem(STEP_KEY);
    } catch {
      /* ignore */
    }
  }, []);

  const next = useCallback(() => {
    setState((s) => {
      if (!s.tour) return s;
      const ni = s.index + 1;
      if (ni >= s.tour.steps.length) {
        endTour();
        return { tour: null, index: 0 };
      }
      goTo(s.tour, ni, projectId);
      return { tour: s.tour, index: ni };
    });
  }, [endTour, goTo, projectId]);

  const prev = useCallback(() => {
    setState((s) => {
      if (!s.tour || s.index === 0) return s;
      const pi = s.index - 1;
      goTo(s.tour, pi, projectId);
      return { tour: s.tour, index: pi };
    });
  }, [goTo, projectId]);

  const skip = useCallback(() => endTour(), [endTour]);
  const finish = useCallback(() => endTour(), [endTour]);

  const resetTourState = useCallback(() => {
    try {
      localStorage.removeItem(SEEN_KEY);
      localStorage.removeItem(STEP_KEY);
      localStorage.removeItem("onboarding_seen");
      localStorage.removeItem("demo_autoplay_seen");
    } catch {
      /* ignore */
    }
    setState({ tour: null, index: 0 });
  }, []);

  // Resume an in-progress tour after a reload.
  useEffect(() => {
    try {
      const raw = localStorage.getItem(STEP_KEY);
      if (raw) {
        const saved = JSON.parse(raw) as { tourId: string; index: number; projectId?: string };
        const t = getTour(saved.tourId);
        if (t && saved.index < t.steps.length) {
          setProjectId(saved.projectId);
          setState({ tour: t, index: saved.index });
        }
      }
    } catch {
      /* ignore */
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const value = useMemo<TourContextValue>(
    () => ({
      active: tour != null,
      tour,
      index,
      step: tour ? tour.steps[index] ?? null : null,
      startTour,
      next,
      prev,
      skip,
      finish,
      resetTourState,
    }),
    [tour, index, startTour, next, prev, skip, finish, resetTourState]
  );

  return (
    <TourContext.Provider value={value}>
      {children}
      <TourOverlay />
    </TourContext.Provider>
  );
}
