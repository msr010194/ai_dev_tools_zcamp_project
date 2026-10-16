export const preview = (body: string) => (body.length > 140 ? body.slice(0, 140) + "..." : body);
