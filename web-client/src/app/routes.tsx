import type { ReactNode } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth-provider";
import { ProfilePage } from "../pages/profile-page";
import { RegistrationPage } from "../pages/registration-page";
import { SignInPage } from "../pages/sign-in-page";
import { SupplierDetailPage } from "../pages/supplier-detail-page";
import { SupplierListPage } from "../pages/supplier-list-page";
import { VerifyEmailPage } from "../pages/verify-email-page";

function SessionLoading() {
  return <main className="session-loading"><span className="loading-dot" />Checking your session</main>;
}

function ProtectedRoute({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  if (status === "restoring") return <SessionLoading />;
  return status === "authenticated" ? children : <Navigate replace to="/sign-in" />;
}

function PublicRoute({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  if (status === "restoring") return <SessionLoading />;
  return status === "authenticated" ? <Navigate replace to="/profile" /> : children;
}

function FallbackRoute() {
  const { status } = useAuth();
  if (status === "restoring") return <SessionLoading />;
  return <Navigate replace to={status === "authenticated" ? "/profile" : "/sign-in"} />;
}

export function AppRoutes() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<FallbackRoute />} />
        <Route path="/sign-in" element={<PublicRoute><SignInPage /></PublicRoute>} />
        <Route path="/register" element={<PublicRoute><RegistrationPage /></PublicRoute>} />
        <Route path="/verify-email" element={<PublicRoute><VerifyEmailPage /></PublicRoute>} />
        <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
        <Route path="/suppliers" element={<ProtectedRoute><SupplierListPage /></ProtectedRoute>} />
        <Route path="/suppliers/:supplierId" element={<ProtectedRoute><SupplierDetailPage /></ProtectedRoute>} />
        <Route path="*" element={<FallbackRoute />} />
      </Routes>
    </BrowserRouter>
  );
}
