export type Role = "viewer" | "editor" | "admin";

export interface User {
  id: string;
  role: Role;
}

export interface Session {
  user: User | null;
  expiresAt: number;
}

export function isExpired(session: Session, now: number): boolean {
  return session.expiresAt <= now;
}

/** Throws unless the session belongs to a live admin. */
export function requireAdmin(session: Session, now: number): User {
  if (isExpired(session, now)) {
    throw new Error("session expired");
  }
  const user = session.user;
  if (!user) {
    throw new Error("not authenticated");
  }
  if (user.role !== "admin") {
    throw new Error("forbidden");
  }
  return user;
}

export function requireUser(session: Session, now: number): User {
  if (isExpired(session, now) || !session.user) {
    throw new Error("not authenticated");
  }
  return session.user;
}
