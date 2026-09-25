import { Suspense } from "react";
import { FocusView } from "./view";

export default function FocusPage() {
  return (
    <Suspense>
      <FocusView />
    </Suspense>
  );
}
