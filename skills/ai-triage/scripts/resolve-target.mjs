const unsupported = (reason) => ({ status: "unsupported", reason });
const needsAnswer = (field) => ({ status: "needs-answer", field });

function pathParts(url) {
  try {
    return url.pathname
      .split("/")
      .filter(Boolean)
      .map((part) => decodeURIComponent(part));
  } catch {
    return null;
  }
}

function isSafePart(part) {
  return (
    typeof part === "string" &&
    Boolean(part.trim()) &&
    part !== "." &&
    part !== ".." &&
    !/[\/\\\u0000-\u001f\u007f]/.test(part)
  );
}

function parseGitHub(url) {
  if (
    url.protocol !== "https:" ||
    url.port ||
    !["github.com", "www.github.com"].includes(url.hostname.toLowerCase()) ||
    url.username ||
    url.password
  ) {
    return null;
  }

  const parts = pathParts(url);
  if (!parts) return null;
  if (parts.length < 2) return needsAnswer("project");

  const [owner, rawRepository] = parts;
  const repository = rawRepository.replace(/\.git$/i, "");
  if (!isSafePart(owner) || !isSafePart(repository)) return null;

  return { status: "ready", provider: "github", owner, repository };
}

function parseAzure(url) {
  const hostname = url.hostname.toLowerCase();
  const isServicesHost =
    hostname === "dev.azure.com" ||
    (hostname.endsWith(".visualstudio.com") &&
      hostname !== "visualstudio.com");
  if (
    !isServicesHost ||
    url.protocol !== "https:" ||
    url.port ||
    url.username ||
    url.password
  ) {
    return null;
  }

  const parts = pathParts(url);
  if (!parts || parts.some((part) => !isSafePart(part))) {
    return unsupported("Invalid Azure DevOps URL");
  }

  const organization = hostname === "dev.azure.com"
    ? parts[0]
    : hostname.slice(0, -".visualstudio.com".length);
  const project = hostname === "dev.azure.com" ? parts[1] : parts[0];
  const target = {
    status: "ready",
    provider: "azure-devops",
    organization,
    project,
  };
  const teamIndex = parts.indexOf("t");
  if (teamIndex >= 0 && isSafePart(parts[teamIndex + 1])) {
    target.team = parts[teamIndex + 1];
  } else {
    const boardsIndex = parts.indexOf("_boards");
    if (boardsIndex >= 3 && isSafePart(parts[boardsIndex - 1])) {
      target.team = parts[boardsIndex - 1];
    }
  }

  const boardsIndex = parts.indexOf("_boards");
  if (boardsIndex >= 0 && !parts[boardsIndex + 1]) {
    target.missingBoard = true;
  }

  const backlogIndex = parts.indexOf("backlogs");
  if (backlogIndex >= 0 && isSafePart(parts[backlogIndex + 1])) {
    const backlogLevel = parts[backlogIndex + 1];
    if (backlogLevel.toLowerCase() !== "board") {
      target.backlogLevel = backlogLevel;
    }
  }
  return target;
}

function parseUrl(value) {
  if (typeof value !== "string" || !value.trim()) return null;
  let url;
  try {
    url = new URL(value.trim());
  } catch {
    return unsupported("Invalid target URL");
  }

  const hostname = url.hostname.toLowerCase();
  if (hostname === "github.com" || hostname === "www.github.com") {
    return parseGitHub(url) ?? unsupported("Unsupported GitHub URL");
  }
  if (
    hostname === "dev.azure.com" ||
    (hostname.endsWith(".visualstudio.com") && hostname !== "visualstudio.com")
  ) {
    return parseAzure(url) ?? unsupported("Unsupported Azure DevOps Services URL");
  }
  if (/\/tfs(?:\/|$)/i.test(url.pathname)) {
    return unsupported("Azure DevOps Server is not supported");
  }
  return unsupported("Only GitHub and Azure DevOps Services URLs are supported");
}

function parseRemote(value) {
  if (typeof value !== "string" || !value.trim()) return null;
  const remote = value.trim();
  let url;

  const scpRemote = remote.match(/^(?:[^@/]+@)?github\.com:([^?#]+)$/i);
  if (scpRemote) {
    try {
      url = new URL(`https://github.com/${scpRemote[1]}`);
    } catch {
      return null;
    }
  } else {
    try {
      url = new URL(remote);
    } catch {
      if (/\/tfs(?:\/|$)/i.test(remote)) {
        return unsupported("Azure DevOps Server is not supported");
      }
      return null;
    }
  }

  if (
    ["github.com", "www.github.com"].includes(url.hostname.toLowerCase()) &&
    ["https:", "ssh:"].includes(url.protocol)
  ) {
    const parts = pathParts(url);
    if (!parts || parts.length < 2) return null;
    const [owner, rawRepository] = parts;
    const repository = rawRepository.replace(/\.git$/i, "");
    if (!isSafePart(owner) || !isSafePart(repository)) return null;
    return { provider: "github", owner, repository };
  }

  const hostname = url.hostname.toLowerCase();
  if (
    url.protocol === "https:" &&
    !url.port &&
    (hostname === "dev.azure.com" ||
      (hostname.endsWith(".visualstudio.com") && hostname !== "visualstudio.com"))
  ) {
    const parts = pathParts(url);
    if (!parts || parts.some((part) => !isSafePart(part))) return null;
    const organization =
      hostname === "dev.azure.com"
        ? parts[0]
        : hostname.slice(0, -".visualstudio.com".length);
    const project = hostname === "dev.azure.com" ? parts[1] : parts[0];
    if (!isSafePart(organization) || !isSafePart(project)) return null;
    return {
      provider: "azure-devops",
      organization,
      project,
    };
  }
  if (/\/tfs(?:\/|$)/i.test(url.pathname)) {
    return unsupported("Azure DevOps Server is not supported");
  }
  return null;
}

function remoteKey(target) {
  return target.provider === "github"
    ? `github:${target.owner}/${target.repository}`.toLowerCase()
    : `azure-devops:${target.organization}/${target.project}`.toLowerCase();
}

function remoteConflictField(targets) {
  if (new Set(targets.map((target) => target.provider)).size > 1) {
    return "provider";
  }
  return "project";
}

function selectionFor(input, target) {
  const selection = input.selection;
  if (!selection || typeof selection !== "object") return target;

  if (selection.provider && selection.provider !== target.provider) {
    return needsAnswer("provider");
  }
  if (target.provider !== "azure-devops") return target;

  const selectedValues = {
    organization: selection.organization,
    project: selection.project,
    team: selection.team,
    board: selection.board,
    backlogLevel: selection.backlog ?? selection.backlogLevel,
  };
  const sourceValues = {
    organization: target.organization,
    project: target.project,
    team: target.team,
    board: target.board,
    backlogLevel: target.backlogLevel,
  };
  const fieldFor = {
    organization: "project",
    project: "project",
    team: "team",
    board: "board",
    backlogLevel: "backlog",
  };

  for (const [key, selected] of Object.entries(selectedValues)) {
    if (typeof selected !== "string" || !selected.trim()) continue;
    if (
      sourceValues[key] &&
      sourceValues[key].toLowerCase() !== selected.trim().toLowerCase()
    ) {
      return needsAnswer(fieldFor[key]);
    }
    sourceValues[key] = selected.trim();
  }

  return {
    ...target,
    ...sourceValues,
    backlog: sourceValues.backlogLevel,
  };
}

function azureFromBoards(remote, discoveredBoards = []) {
  const boards = (Array.isArray(discoveredBoards) ? discoveredBoards : []).filter(
    (board) =>
      board &&
      board.organization === remote.organization &&
      board.project === remote.project &&
      isSafePart(board.team) &&
      (board.board === undefined || isSafePart(board.board)) &&
      isSafePart(board.backlogLevel),
  );
  const uniqueBoards = [
    ...new Map(
      boards.map((board) => [
        [
          board.organization,
          board.project,
          board.team,
          board.board ?? "",
          board.backlogLevel,
        ].join("\u0000"),
        board,
      ]),
    ).values(),
  ];

  for (const [key, field] of [
    ["team", "team"],
    ["board", "board"],
    ["backlogLevel", "backlog"],
  ]) {
    if (new Set(uniqueBoards.map((board) => board[key]).filter(Boolean)).size > 1) {
      return needsAnswer(field);
    }
  }
  if (uniqueBoards.length !== 1) return needsAnswer("team");

  const [board] = uniqueBoards;
  return {
    status: "ready",
    provider: "azure-devops",
    organization: remote.organization,
    project: remote.project,
    team: board.team,
    ...(board.board ? { board: board.board } : {}),
    backlogLevel: board.backlogLevel,
    backlog: board.backlogLevel,
  };
}

export function resolveTarget(input = {}) {
  const explicitUrl = input.explicitUrl ?? input.url;
  if (typeof explicitUrl === "string" && explicitUrl.trim()) {
    const target = parseUrl(explicitUrl);
    if (target.status !== "ready") return target;
    return validateAzureTarget(selectionFor(input, target));
  }

  const remotes = Array.isArray(input.remotes) ? input.remotes : [];
  const parsedRemotes = remotes.map(parseRemote);
  const unsupportedRemote = parsedRemotes.find(
    (target) => target?.status === "unsupported",
  );
  if (unsupportedRemote) return unsupportedRemote;

  const targets = parsedRemotes.filter(Boolean);
  if (targets.length !== remotes.length) return needsAnswer("provider");
  const uniqueTargets = [...new Map(targets.map((target) => [remoteKey(target), target])).values()];
  if (!uniqueTargets.length) {
    if (input.selection?.provider === "azure-devops") {
      return validateAzureTarget(selectionFor(input, {
        status: "ready",
        provider: "azure-devops",
      }));
    }
    return needsAnswer("provider");
  }
  if (uniqueTargets.length > 1) {
    return needsAnswer(remoteConflictField(uniqueTargets));
  }

  const [remote] = uniqueTargets;
  if (remote.provider === "github") return selectionFor(input, { status: "ready", ...remote });
  const target = azureFromBoards(remote, input.discoveredBoards);
  if (target.status !== "ready") {
    if (!input.selection) return target;
    return validateAzureTarget(
      selectionFor(input, { status: "ready", ...remote }),
    );
  }
  return validateAzureTarget(selectionFor(input, target));
}

function validateAzureTarget(target) {
  if (target.status !== "ready" || target.provider !== "azure-devops") return target;
  if (!isSafePart(target.organization) || !isSafePart(target.project)) {
    return needsAnswer("project");
  }
  if (!isSafePart(target.team)) return needsAnswer("team");
  if (target.missingBoard && !target.board) return needsAnswer("board");
  if (target.board && !isSafePart(target.board)) return needsAnswer("board");
  if (!isSafePart(target.backlogLevel)) return needsAnswer("backlog");
  return target;
}

export async function resolveTargetAndRead(input = {}, read) {
  const target = resolveTarget(input);
  if (target.status !== "ready" || target.provider !== "azure-devops") {
    return target;
  }

  const board = target.board;
  const backlog = target.backlog ?? target.backlogLevel;
  if (!isSafePart(board)) return needsAnswer("board");
  if (!isSafePart(backlog)) return needsAnswer("backlog");
  if (typeof read !== "function") return needsAnswer("backlog");

  const scope = {
    provider: "azure-devops",
    organization: target.organization,
    project: target.project,
    team: target.team,
    board,
    backlog,
  };
  await read(scope);
  return { status: "read", target: scope };
}
