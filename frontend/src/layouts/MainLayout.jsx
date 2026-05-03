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
    <main className="min-h-screen bg-slate-950 text-slate-100 flex flex-col lg:flex-row">
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
            className="absolute inset-0 bg-slate-950/70 backdrop-blur-sm"
            onClick={onCloseMobileMenu}
          />
          <div className="absolute right-0 top-0 h-full w-[85vw] max-w-sm overflow-y-auto border-l border-slate-800 bg-slate-900 shadow-2xl">
            {children.mobileSidebar}
          </div>
        </div>
      )}

      {children.content || children}
    </main>
  );
}

export default MainLayout;
