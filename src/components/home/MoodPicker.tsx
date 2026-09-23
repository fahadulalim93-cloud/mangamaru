"use client";
import { MOODS, Mood } from "@/lib/anilist";

interface MoodPickerProps {
  activeMood: Mood;
  onPick: (mood: Mood) => void;
}

export function MoodPicker({ activeMood, onPick }: MoodPickerProps) {
  return (
    <section className="mood-picker" style={{ ["--mood-color" as string]: activeMood.color }}>
      <div className="mood-header">
        <h2 className="mood-title">Pick a mood</h2>
        <p className="mood-desc">{activeMood.description}</p>
      </div>
      <div className="mood-buttons">
        {MOODS.map((m) => (
          <button
            key={m.id}
            className={`mood-btn ${activeMood.id === m.id ? "active" : ""}`}
            onClick={() => onPick(m)}
            style={{ ["--mood-color" as string]: m.color }}
            title={m.description}
          >
            <span className="mood-emoji">{m.emoji}</span>
            <span className="mood-label">{m.label}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
