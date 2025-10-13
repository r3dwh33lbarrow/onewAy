export interface BaseMessage {
  type: string;
}

export interface ErrorMessage extends BaseMessage {
  type: "error";
  message: string;
}

export interface ConsoleOutput extends BaseMessage {
  type: "console_output";
  from: string;
  output: {
    module_name: string;
    stream: "stdout" | "stderr";
    line: string;
  };
}

export interface EventMessage extends BaseMessage {
  type: "module_started" | "module_exit" | "module_canceled";
  from: string;
  event: {
    module_name: string;
    code: string;
  };
}

export type Message = ErrorMessage | ConsoleOutput | EventMessage;
