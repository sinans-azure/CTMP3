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
    const roles = claims.roles || [];

    return {
      name: account.name || claims.name || "User",
      email: account.username || claims.preferred_username || claims.email || "",
      roles,
      isAdmin: roles.includes(AppRoles.Admin),
      isTrainer: roles.includes(AppRoles.Trainer),
      isStudent: roles.includes(AppRoles.Student),
      isAuthenticated: true,
      userId: claims.oid || account.localAccountId || "",
    };
  }, [accounts]);
}
