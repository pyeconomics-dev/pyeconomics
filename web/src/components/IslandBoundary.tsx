// web/src/components/IslandBoundary.tsx
// Catches an error an island throws while rendering (Phase 5 Step 14): the
// island shows a short notice instead of vanishing, and the error goes to the
// error tracker in a production build (src/lib/error-reporting.ts), its
// message withheld. React offers this only to a class component.
import { Component, type ReactNode } from "react";

import { report, type Island } from "@/lib/error-reporting";

interface Props {
  island: Island;
  children: ReactNode;
}

export default class IslandBoundary extends Component<Props, { failed: boolean }> {
  override state = { failed: false };

  static getDerivedStateFromError(): { failed: boolean } {
    return { failed: true };
  }

  override componentDidCatch(error: unknown): void {
    void report(error, this.props.island);
  }

  override render(): ReactNode {
    if (this.state.failed) {
      return (
        <p className="text-sm" role="alert">
          This part of the page stopped working. Reload the page to try again.
        </p>
      );
    }
    return this.props.children;
  }
}
