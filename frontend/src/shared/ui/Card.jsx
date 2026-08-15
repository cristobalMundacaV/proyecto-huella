export function Card({children,className="",...props}){return <section className={`rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface)] shadow-[var(--shadow-sm)] ${className}`} {...props}>{children}</section>}
export function CardHeader({children,className=""}){return <header className={`border-b border-[var(--border-subtle)] p-[var(--card-padding)] ${className}`}>{children}</header>}
export function CardContent({children,className=""}){return <div className={`p-[var(--card-padding)] ${className}`}>{children}</div>}
export function CardFooter({children,className=""}){return <footer className={`border-t border-[var(--border-subtle)] p-[var(--card-padding)] ${className}`}>{children}</footer>}
