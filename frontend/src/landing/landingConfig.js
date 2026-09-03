export function resolveAppLoginUrl(appUrl) {
  return appUrl ? `${appUrl.replace(/\/$/, "")}/login` : "/app";
}
