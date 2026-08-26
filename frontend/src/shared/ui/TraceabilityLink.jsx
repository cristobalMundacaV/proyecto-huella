import {
    FileText,
} from "lucide-react";

import {
    Button,
} from "./Button";

export default function TraceabilityLink({
    onClick,
    label = "Ver origen",
}) {
    return (
        <Button
            variant="secondary"
            size="sm"
            leftIcon={FileText}
            onClick={onClick}
        >
            {label}
        </Button>
    );
}