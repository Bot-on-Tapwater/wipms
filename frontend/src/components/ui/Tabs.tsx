interface Tab {
  id: string;
  label: string;
}

interface TabsProps {
  tabs: Tab[];
  active: string;
  onChange: (id: string) => void;
}

/** A row of tabs; scrolls sideways on small screens. */
export function Tabs({ tabs, active, onChange }: TabsProps) {
  return (
    <div className="mb-4 overflow-x-auto border-b border-zinc-200">
      <div className="flex min-w-max gap-1" role="tablist">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={tab.id === active}
            onClick={() => onChange(tab.id)}
            className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
              tab.id === active
                ? "border-emerald-600 text-emerald-700"
                : "border-transparent text-zinc-500 hover:text-zinc-900"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
    </div>
  );
}
