import { Link } from "react-router-dom";
import { useOverview, useRequests } from "@/api/hooks";
import { IndustrialHero } from "@/components/media/IndustrialHero";
import { MaterialBand } from "@/components/media/MaterialBand";
import { VISUALS } from "@/components/media/assets";
import { useMainScroll } from "@/components/Shell";
import { RequirementsTable } from "@/components/Workflow";
import { LoadingBlock, ErrorBlock } from "@/components/ui";
export default function Overview() {
  const overview = useOverview();
  const requests = useRequests({
    run_id: overview.data?.latest_run?.id ?? undefined,
    status: "pending",
    limit: 8,
  });
  return (
    <div>
      <IndustrialHero scrollRef={useMainScroll()} />
      <MaterialBand
        asset={VISUALS.gears}
        statement="Steel becomes a requirement. A requirement becomes a decision."
        caption="EVERY LINE BELOW CARRIES ITS OWN EVIDENCE TRAIL"
        vertical="SCROLL TO THE WORK QUEUE"
        height={196}
      />
      <section className="paper-texture px-6 py-10 text-ink md:px-10">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <div className="eyebrow">02 — LATEST RUN / WORK QUEUE</div>
            <h2 className="font-display mt-3 text-[clamp(28px,4vw,40px)]">
              Awaiting a decision
            </h2>
          </div>
          <Link to="/inbox" className="text-ultra underline">
            Open buyer inbox
          </Link>
        </div>
        {requests.isPending ? (
          <LoadingBlock />
        ) : requests.error ? (
          <ErrorBlock error={requests.error} />
        ) : (
          <RequirementsTable
            items={requests.data?.items ?? []}
            runId={overview.data?.latest_run?.id ?? ""}
          />
        )}
      </section>
    </div>
  );
}
