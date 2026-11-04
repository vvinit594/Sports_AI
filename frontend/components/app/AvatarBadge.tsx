import { AVATARS } from "@/types/onboarding";

type AvatarBadgeProps = {
  name: string;
  avatarId: string | null;
  size?: "sm" | "md";
};

export function AvatarBadge({ name, avatarId, size = "sm" }: AvatarBadgeProps) {
  const avatar = AVATARS.find((item) => item.id === avatarId);
  const initials = name.trim().slice(0, 2).toUpperCase() || "PQ";
  const dimension = size === "md" ? "h-12 w-12 text-base" : "h-9 w-9 text-xs";

  return (
    <span
      aria-hidden
      className={`inline-grid ${dimension} place-items-center rounded-full font-display font-semibold text-white`}
      style={{ background: avatar?.accent ?? "#FF3B4A" }}
    >
      {initials}
    </span>
  );
}
