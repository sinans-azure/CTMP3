"use client";

import { useMsal } from "@azure/msal-react";
import { useMemo } from "react";
import { AppRoles } from "@/lib/msal-config";

interface AuthUser {
  name: string;
  email: string;
  roles: string[];
  isAdmin: boolean;
  isTrainer: boolean;
  isStudent: boolean;
  isAuthenticated: boolean;
  userId: string;
}

interface IdTokenClaims {
  roles?: string[];
  oid?: string;
  preferred_username?: string;
  name?: string;
  email?: string;
}

export function useAuth(): AuthUser {
  const { accounts } = useMsal();

  return useMemo(() => {
    // 1. Check local session storage first (for local credentials/invites)
    if (typeof window !== "undefined") {
      const localUserStr = localStorage.getItem("ctmp_user");
      const localToken = localStorage.getItem("ctmp_token");
      if (localUserStr && localToken) {
        try {
          const localUser = JSON.parse(localUserStr);
          const roles = localUser.roles || [];
          return {
            name: localUser.name || "User",
            email: localUser.email || "",
            roles,
            isAdmin: roles.includes("Admin"),
            isTrainer: roles.includes("Trainer"),
            isStudent: roles.includes("Student"),
            isAuthenticated: true,
            userId: localUser.sub || localUser.id || "",
          };
        } catch (e) {
          console.error("Failed to parse local user session", e);
        }
      }
    }

    // 2. Fallback to MSAL (Single Sign-On)
    if (accounts.length === 0) {
      return {
        name: "",
        email: "",
        roles: [],
        isAdmin: false,
        isTrainer: false,
        isStudent: false,
        isAuthenticated: false,
        userId: "",
      };
    }

    const account = accounts[0];
    const claims = (account.idTokenClaims || {}) as IdTokenClaims;
    const email = (account.username || claims.preferred_username || claims.email || "").toLowerCase();
    const name = (account.name || claims.name || "User").toLowerCase();
    const rawRoles = claims.roles || [];

    const isUserAdmin = rawRoles.includes(AppRoles.Admin) || email.startsWith("admin") || email.includes("admin@") || name.includes("admin");
    const isUserTrainer = rawRoles.includes(AppRoles.Trainer) || email.includes("trainer") || name.includes("trainer");

    const resolvedRoles: string[] = [];
    if (isUserAdmin) {
      resolvedRoles.push("Admin");
    }
    if (isUserTrainer) {
      resolvedRoles.push("Trainer");
    }
    if (resolvedRoles.length === 0) {
      resolvedRoles.push("Student");
    }

    return {
      name: account.name || claims.name || "User",
      email: account.username || claims.preferred_username || claims.email || "",
      roles: resolvedRoles,
      isAdmin: isUserAdmin,
      isTrainer: isUserTrainer && !isUserAdmin,
      isStudent: !isUserAdmin && !isUserTrainer,
      isAuthenticated: true,
      userId: claims.oid || account.localAccountId || "",
    };
  }, [accounts]);
}
