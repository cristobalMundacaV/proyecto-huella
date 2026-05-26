export function mapObraOption(obra) {
  return {
    label: obra?.codigo_obra || "",
    value: obra?.codigo_obra || "",
  };
}
