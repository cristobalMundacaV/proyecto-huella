import {
    FileText,
} from "lucide-react";

import {
    Button,
} from "./Button";

export default function TraceabilityLink({
    onClick,
    label = "Ver origen",
    iconOnly = false,
}) {
    return (
        <Button
            variant="secondary"
            size="sm"
            leftIcon={FileText}
            onClick={onClick}
            aria-label={
                iconOnly
                    ? label
                    : undefined
            }
            title={
                iconOnly
                    ? label
                    : undefined
            }
            className={
                iconOnly
                    ? "aspect-square px-2"
                    : ""
            }
        >
            {iconOnly
                ? null
                : label}
        </Button>
    );
}