import Sidebar from "./Sidebar";

function MainLayout({
  activeView,
  children,
  mobileMenuOpen,
  onCloseMobileMenu,
  onOpenMobileMenu,
  onSetActiveView,
  systemStatus,
  mobileMenuButton,
}) {
  return (
    <main className="flex min-h-screen flex-col bg-[var(--bg-main)] text-[var(--text-main)] lg:flex-row">
      {mobileMenuButton?.({ onOpenMobileMenu })}

      <div className="hidden lg:block">
        <Sidebar
          activeView={activeView}
          onSetActiveView={onSetActiveView}
          systemStatus={systemStatus}
        />
      </div>

      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-slate-950/30 backdrop-blur-sm"
            onClick={onCloseMobileMenu}
          />
          <div className="absolute right-0 top-0 h-full w-[85vw] max-w-sm overflow-y-auto border-l border-white/10 bg-[var(--sidebar)] shadow-2xl">
            {children.mobileSidebar}
          </div>
        </div>
      )}

      {children.content || children}
    </main>
  );
}

export default MainLayout;
