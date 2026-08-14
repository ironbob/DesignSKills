package org.slf4j;

public final class LoggerFactory {
    private LoggerFactory() {}

    public static Logger getLogger(Class<?> owner) {
        return new StdoutLogger(owner.getSimpleName());
    }

    private record StdoutLogger(String owner) implements Logger {
        @Override
        public void info(String message, Object... arguments) {
            System.out.println("INFO [" + owner + "] " + format(message, arguments));
        }

        @Override
        public void error(String message, Object... arguments) {
            System.err.println("ERROR [" + owner + "] " + format(message, arguments));
        }

        private static String format(String message, Object... arguments) {
            String rendered = message;
            for (Object argument : arguments) {
                rendered = rendered.replaceFirst("\\{}", String.valueOf(argument));
            }
            return rendered;
        }
    }
}
